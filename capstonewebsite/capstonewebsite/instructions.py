import slicer
import vtk
import qt

# ------------------------------------------
# Install/import speech packages if needed
# ------------------------------------------
try:
    import speech_recognition as sr
except ImportError:
    slicer.util.pip_install("SpeechRecognition")
    import speech_recognition as sr

try:
    import pyaudio  # required for Microphone()
except ImportError:
    slicer.util.pip_install("PyAudio")
    import pyaudio

# ==========================================
# Central Line Instruction HUD for Slicer
# - Fixed instruction text in 3D view
# - Clickable 2D PREV / NEXT buttons
# - Keyboard controls: N and P
# - Voice controls: "next" and "previous"
# ==========================================

# -----------------------------
# Procedure steps
# -----------------------------
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

# -----------------------------
# Global state
# -----------------------------
currentStep = 0

# -----------------------------
# Access 3D view
# -----------------------------
layoutManager = slicer.app.layoutManager()
threeDWidget = layoutManager.threeDWidget(0)
view = threeDWidget.threeDView()
renderWindow = view.renderWindow()
renderer = renderWindow.GetRenderers().GetFirstRenderer()
interactor = view.interactor()

# -----------------------------
# Clean up old version if rerun
# -----------------------------
oldActorNames = [
    "cliTitleActor",
    "cliStepActor",
    "cliInstructionActor",
    "cliHintActor",
    "cliNextButtonActor",
    "cliPrevButtonActor",
    "cliVoiceStatusActor",
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

# Stop old voice listener if script is rerun
if hasattr(slicer, "cliVoiceStopListening"):
    try:
        slicer.cliVoiceStopListening(wait_for_stop=False)
    except Exception:
        pass

# -----------------------------
# Helper to make text actors
# -----------------------------
def makeTextActor(text, x, y, fontSize=20, bold=False, color=(1, 1, 1)):
    actor = vtk.vtkTextActor()
    actor.SetInput(text)
    prop = actor.GetTextProperty()
    prop.SetFontSize(fontSize)
    prop.SetBold(1 if bold else 0)
    prop.SetColor(color[0], color[1], color[2])
    actor.SetDisplayPosition(x, y)
    renderer.AddActor2D(actor)
    return actor

# -----------------------------
# Layout positions
# -----------------------------
TITLE_X = 35
TITLE_Y = 150

STEP_X = 35
STEP_Y = 112

INSTR_X = 35
INSTR_Y = 78

HINT_X = 35
HINT_Y = 42

VOICE_X = 35
VOICE_Y = 15

PREV_X = 520
PREV_Y = 42

NEXT_X = 650
NEXT_Y = 42

BUTTON_W = 100
BUTTON_H = 35

# -----------------------------
# Create overlay text
# -----------------------------
titleActor = makeTextActor(
    "Central Line Insertion Guidance",
    TITLE_X, TITLE_Y,
    fontSize=24, bold=True, color=(1, 1, 1)
)

stepActor = makeTextActor(
    "",
    STEP_X, STEP_Y,
    fontSize=20, bold=True, color=(1.0, 1.0, 0.2)
)

instructionActor = makeTextActor(
    "",
    INSTR_X, INSTR_Y,
    fontSize=18, bold=False, color=(1, 1, 1)
)

hintActor = makeTextActor(
    "Keyboard: N = NEXT    P = PREV    Voice: say NEXT or PREVIOUS",
    HINT_X, HINT_Y,
    fontSize=16, bold=False, color=(0.7, 0.9, 1.0)
)

voiceStatusActor = makeTextActor(
    "Voice: starting...",
    VOICE_X, VOICE_Y,
    fontSize=14, bold=False, color=(0.8, 1.0, 0.8)
)

prevButtonActor = makeTextActor(
    "[ PREV ]",
    PREV_X, PREV_Y,
    fontSize=22, bold=True, color=(1.0, 1.0, 1.0)
)

nextButtonActor = makeTextActor(
    "[ NEXT ]",
    NEXT_X, NEXT_Y,
    fontSize=22, bold=True, color=(1.0, 1.0, 1.0)
)

# Store actors on slicer so rerunning works
slicer.cliTitleActor = titleActor
slicer.cliStepActor = stepActor
slicer.cliInstructionActor = instructionActor
slicer.cliHintActor = hintActor
slicer.cliVoiceStatusActor = voiceStatusActor
slicer.cliPrevButtonActor = prevButtonActor
slicer.cliNextButtonActor = nextButtonActor

# -----------------------------
# UI helpers
# -----------------------------
def renderNow():
    renderWindow.Render()

def runOnMainThread(fn, *args, **kwargs):
    qt.QTimer.singleShot(0, lambda: fn(*args, **kwargs))

def setVoiceStatus(text):
    voiceStatusActor.SetInput(text)
    renderNow()

# -----------------------------
# Update display
# -----------------------------
def updateHUD():
    global currentStep
    stepActor.SetInput(f"Step {currentStep + 1} / {len(steps)}")
    instructionActor.SetInput(steps[currentStep])
    renderNow()

# -----------------------------
# Navigation functions
# -----------------------------
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

# -----------------------------
# Click detection
# -----------------------------
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

# -----------------------------
# Voice command handling
# -----------------------------
VOICE_NEXT_WORDS = ["next", "next step", "go next", "continue", "forward"]
VOICE_PREV_WORDS = ["previous", "prev", "go back", "back", "previous step"]

def handleVoiceCommand(text):
    t = text.lower().strip()
    print(f"VOICE HEARD: {t}")

    if any(cmd in t for cmd in VOICE_NEXT_WORDS):
        runOnMainThread(setVoiceStatus, f"Voice heard: {text}  -> NEXT")
        runOnMainThread(nextStep)
        return

    if any(cmd in t for cmd in VOICE_PREV_WORDS):
        runOnMainThread(setVoiceStatus, f"Voice heard: {text}  -> PREV")
        runOnMainThread(prevStep)
        return

    runOnMainThread(setVoiceStatus, f"Voice heard: {text}  -> ignored")

def voiceCallback(recognizer, audio):
    try:
        # Fast/simple option for short commands
        text = recognizer.recognize_google(audio)
        handleVoiceCommand(text)

    except sr.UnknownValueError:
        runOnMainThread(setVoiceStatus, "Voice: command not understood")
    except sr.RequestError as e:
        runOnMainThread(setVoiceStatus, f"Voice service error: {e}")
    except Exception as e:
        runOnMainThread(setVoiceStatus, f"Voice error: {e}")

def startVoiceControl():
    try:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.5

        microphone = sr.Microphone()

        setVoiceStatus("Voice: calibrating microphone...")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)

        stopListening = recognizer.listen_in_background(
            microphone,
            voiceCallback,
            phrase_time_limit=2
        )

        slicer.cliVoiceRecognizer = recognizer
        slicer.cliVoiceMicrophone = microphone
        slicer.cliVoiceStopListening = stopListening

        setVoiceStatus("Voice: listening for NEXT or PREVIOUS")
        print("Voice control started.")

    except Exception as e:
        setVoiceStatus(f"Voice init failed: {e}")
        print(f"Voice control failed to start: {e}")

def stopVoiceControl():
    if hasattr(slicer, "cliVoiceStopListening"):
        try:
            slicer.cliVoiceStopListening(wait_for_stop=False)
            setVoiceStatus("Voice: stopped")
            print("Voice control stopped.")
        except Exception as e:
            print(f"Error stopping voice control: {e}")

slicer.cliStartVoiceControl = startVoiceControl
slicer.cliStopVoiceControl = stopVoiceControl

# -----------------------------
# Attach observers
# -----------------------------
leftClickObserverTag = interactor.AddObserver("LeftButtonPressEvent", onLeftClick)
keyPressObserverTag = interactor.AddObserver("KeyPressEvent", onKeyPress)

slicer.cliLeftClickObserverTag = leftClickObserverTag
slicer.cliKeyPressObserverTag = keyPressObserverTag

# -----------------------------
# Initialize
# -----------------------------
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
print("  Restart voice: slicer.cliStartVoiceControl()")
print("  Stop voice: slicer.cliStopVoiceControl()")