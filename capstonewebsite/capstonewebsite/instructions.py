import slicer
import vtk
import qt

# macOS voice recognition
from AppKit import NSSpeechRecognizer, NSObject

# ==========================================
# Central Line Instruction HUD for Slicer
# - Fixed instruction text in 3D view
# - Clickable 2D PREV / NEXT buttons
# - Keyboard controls: N and P
# - Voice controls on macOS: "next", "previous"
# ==========================================

steps = [
    "Verify patient identity and sterile setup",
    "Identify target vein using ultrasound",
    "Confirm vein compressibility and anatomy",
    "Insert needle under ultrasound guidance",
    "Confirm venous access",
    "Advance guidewire",
    "Dilate the tract",
    "Insert catheter",
    "Secure the line and confirm placement"
]

currentStep = 0

layoutManager = slicer.app.layoutManager()
threeDWidget = layoutManager.threeDWidget(0)
view = threeDWidget.threeDView()
renderWindow = view.renderWindow()
renderer = renderWindow.GetRenderers().GetFirstRenderer()
interactor = view.interactor()

oldActorNames = [
    "cliTitleActor",
    "cliStepActor",
    "cliInstructionActor",
    "cliHintActor",
    "cliNextButtonActor",
    "cliPrevButtonActor",
    "cliVoiceActor",
]

for attr in oldActorNames:
    if hasattr(slicer, attr):
        try:
            renderer.RemoveActor2D(getattr(slicer, attr))
        except Exception:
            pass

for obsName in ["cliLeftClickObserverTag", "cliKeyPressObserverTag"]:
    if hasattr(slicer, obsName):
        try:
            interactor.RemoveObserver(getattr(slicer, obsName))
        except Exception:
            pass

if hasattr(slicer, "cliSpeechRecognizer"):
    try:
        slicer.cliSpeechRecognizer.stopListening()
    except Exception:
        pass


def makeTextActor(text, x, y, fontSize=20, bold=False, color=(1,1,1)):
    actor = vtk.vtkTextActor()
    actor.SetInput(text)
    prop = actor.GetTextProperty()
    prop.SetFontSize(fontSize)
    prop.SetBold(1 if bold else 0)
    prop.SetColor(*color)
    actor.SetDisplayPosition(x, y)
    renderer.AddActor2D(actor)
    return actor


TITLE_X, TITLE_Y = 35, 150
STEP_X, STEP_Y = 35, 112
INSTR_X, INSTR_Y = 35, 78
HINT_X, HINT_Y = 35, 42
VOICE_X, VOICE_Y = 35, 16
PREV_X, PREV_Y = 520, 42
NEXT_X, NEXT_Y = 650, 42
BUTTON_W, BUTTON_H = 100, 35

titleActor = makeTextActor(
    "Central Line Insertion Guidance",
    TITLE_X, TITLE_Y, fontSize=24, bold=True, color=(1,1,1)
)

stepActor = makeTextActor(
    "", STEP_X, STEP_Y, fontSize=20, bold=True, color=(1.0, 1.0, 0.2)
)

instructionActor = makeTextActor(
    "", INSTR_X, INSTR_Y, fontSize=18, bold=False, color=(1,1,1)
)

hintActor = makeTextActor(
    "Keyboard: N = NEXT    P = PREV    Voice: say NEXT or PREVIOUS",
    HINT_X, HINT_Y, fontSize=16, bold=False, color=(0.7, 0.9, 1.0)
)

voiceActor = makeTextActor(
    "Voice: starting...",
    VOICE_X, VOICE_Y, fontSize=14, bold=False, color=(0.8, 1.0, 0.8)
)

prevButtonActor = makeTextActor(
    "[ PREV ]", PREV_X, PREV_Y, fontSize=22, bold=True, color=(1,1,1)
)

nextButtonActor = makeTextActor(
    "[ NEXT ]", NEXT_X, NEXT_Y, fontSize=22, bold=True, color=(1,1,1)
)

slicer.cliTitleActor = titleActor
slicer.cliStepActor = stepActor
slicer.cliInstructionActor = instructionActor
slicer.cliHintActor = hintActor
slicer.cliVoiceActor = voiceActor
slicer.cliPrevButtonActor = prevButtonActor
slicer.cliNextButtonActor = nextButtonActor


def renderNow():
    renderWindow.Render()

def runOnMainThread(fn, *args, **kwargs):
    qt.QTimer.singleShot(0, lambda: fn(*args, **kwargs))

def setVoiceStatus(text):
    voiceActor.SetInput(text)
    renderNow()

def updateHUD():
    global currentStep
    stepActor.SetInput(f"Step {currentStep + 1} / {len(steps)}")
    instructionActor.SetInput(steps[currentStep])
    renderNow()

def nextStep():
    global currentStep
    if currentStep < len(steps) - 1:
        currentStep += 1
    updateHUD()
    print(f"NEXT -> Step {currentStep + 1}: {steps[currentStep]}")

def prevStep():
    global currentStep
    if currentStep > 0:
        currentStep -= 1
    updateHUD()
    print(f"PREV -> Step {currentStep + 1}: {steps[currentStep]}")

slicer.cliNextStep = nextStep
slicer.cliPrevStep = prevStep


def insideBox(px, py, x, y, w, h):
    return (x <= px <= x + w) and (y <= py <= y + h)

def onLeftClick(caller, event):
    clickX, clickY = interactor.GetEventPosition()

    if insideBox(clickX, clickY, PREV_X, PREV_Y, BUTTON_W, BUTTON_H):
        prevStep()
        return

    if insideBox(clickX, clickY, NEXT_X, NEXT_Y, BUTTON_W, BUTTON_H):
        nextStep()
        return

def onKeyPress(caller, event):
    key = interactor.GetKeySym()
    if not key:
        return
    key = key.lower()

    if key == "n":
        nextStep()
    elif key == "p":
        prevStep()


class SpeechDelegate(NSObject):
    def speechRecognizer_didRecognizeCommand_(self, recognizer, command):
        cmd = str(command).lower().strip()
        print("VOICE HEARD:", cmd)

        if cmd == "next":
            runOnMainThread(setVoiceStatus, "Voice heard: next -> NEXT")
            runOnMainThread(nextStep)
        elif cmd in ("previous", "prev", "back"):
            runOnMainThread(setVoiceStatus, f"Voice heard: {cmd} -> PREV")
            runOnMainThread(prevStep)
        else:
            runOnMainThread(setVoiceStatus, f"Voice heard: {cmd} -> ignored")


def startVoiceControl():
    try:
        delegate = SpeechDelegate.alloc().init()
        recognizer = NSSpeechRecognizer.alloc().init()

        recognizer.setCommands_(["next", "previous", "prev", "back"])
        recognizer.setBlocksOtherRecognizers_(False)
        recognizer.setDelegate_(delegate)
        recognizer.startListening()

        slicer.cliSpeechDelegate = delegate
        slicer.cliSpeechRecognizer = recognizer

        setVoiceStatus("Voice: listening for NEXT or PREVIOUS")
        print("macOS voice control started.")

    except Exception as e:
        setVoiceStatus(f"Voice init failed: {e}")
        print("Voice init failed:", e)

def stopVoiceControl():
    if hasattr(slicer, "cliSpeechRecognizer"):
        try:
            slicer.cliSpeechRecognizer.stopListening()
            setVoiceStatus("Voice: stopped")
            print("Voice stopped.")
        except Exception as e:
            print("Voice stop failed:", e)

slicer.cliStartVoiceControl = startVoiceControl
slicer.cliStopVoiceControl = stopVoiceControl


leftClickObserverTag = interactor.AddObserver("LeftButtonPressEvent", onLeftClick)
keyPressObserverTag = interactor.AddObserver("KeyPressEvent", onKeyPress)

slicer.cliLeftClickObserverTag = leftClickObserverTag
slicer.cliKeyPressObserverTag = keyPressObserverTag

renderer.ResetCamera()
updateHUD()
startVoiceControl()

print("Central line instruction HUD ready.")
print("Controls:")
print("  Click [ NEXT ] or [ PREV ]")
print("  Press N for next")
print("  Press P for previous")
print("  Say NEXT or PREVIOUS")
print("  Manual test: slicer.cliNextStep() or slicer.cliPrevStep()")