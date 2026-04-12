import slicer
import vtk
import qt
import os

# ==========================================
# Central Line Instruction HUD for Slicer
# - Fixed instruction text in 3D view
# - Clickable 2D PREV / NEXT buttons
# - Keyboard controls: N and P
# - External voice control via file polling
#   Voice script writes:
#       /tmp/slicer_voice_command.txt
#   with contents:
#       "next" or "prev"
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
COMMAND_FILE = "/tmp/slicer_voice_command.txt"

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
    "cliVoiceStatusActor",
    "cliNextButtonActor",
    "cliPrevButtonActor"
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

if hasattr(slicer, "cliVoiceTimer"):
    try:
        slicer.cliVoiceTimer.stop()
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
    "Keyboard: N = NEXT    P = PREV    Voice: external listener active",
    HINT_X, HINT_Y,
    fontSize=16, bold=False, color=(0.7, 0.9, 1.0)
)

voiceStatusActor = makeTextActor(
    "Voice: waiting for external commands",
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

# store them on slicer so rerunning works
slicer.cliTitleActor = titleActor
slicer.cliStepActor = stepActor
slicer.cliInstructionActor = instructionActor
slicer.cliHintActor = hintActor
slicer.cliVoiceStatusActor = voiceStatusActor
slicer.cliPrevButtonActor = prevButtonActor
slicer.cliNextButtonActor = nextButtonActor

# -----------------------------
# Update display
# -----------------------------
def updateHUD():
    global currentStep
    stepActor.SetInput(f"Step {currentStep + 1} / {len(steps)}")
    instructionActor.SetInput(steps[currentStep])
    renderWindow.Render()

def setVoiceStatus(text):
    voiceStatusActor.SetInput(text)
    renderWindow.Render()

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

# expose for manual testing
slicer.cliNextStep = nextStep
slicer.cliPrevStep = prevStep

# -----------------------------
# Click detection using screen coordinates
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

# attach observers
leftClickObserverTag = interactor.AddObserver("LeftButtonPressEvent", onLeftClick)
keyPressObserverTag = interactor.AddObserver("KeyPressEvent", onKeyPress)

slicer.cliLeftClickObserverTag = leftClickObserverTag
slicer.cliKeyPressObserverTag = keyPressObserverTag

# -----------------------------
# External voice command polling
# -----------------------------
def checkVoiceCommand():
    if not os.path.exists(COMMAND_FILE):
        return

    try:
        with open(COMMAND_FILE, "r") as f:
            cmd = f.read().strip().lower()

        os.remove(COMMAND_FILE)

        if cmd == "next":
            setVoiceStatus("Voice heard: NEXT")
            nextStep()

        elif cmd == "prev":
            setVoiceStatus("Voice heard: PREV")
            prevStep()

        else:
            setVoiceStatus(f"Voice heard: ignored ({cmd})")

    except Exception as e:
        setVoiceStatus("Voice read error")
        print("Voice read error:", e)

voiceTimer = qt.QTimer()
voiceTimer.timeout.connect(checkVoiceCommand)
voiceTimer.start(500)  # check every 500 ms

slicer.cliVoiceTimer = voiceTimer

# -----------------------------
# Initialize
# -----------------------------
renderer.ResetCamera()
updateHUD()

print("Central line instruction HUD ready.")
print("Controls:")
print("  Click [ NEXT ] or [ PREV ] in the top-right 3D view")
print("  Press N for next")
print("  Press P for previous")
print("  Manual test: slicer.cliNextStep() or slicer.cliPrevStep()")
print("  External voice polling active")
print(f"  Watching command file: {COMMAND_FILE}")