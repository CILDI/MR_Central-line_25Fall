import slicer
import vtk
import qt
import os

#clean central line instruction overlay system with top-aligned hud
#displays step number, main instruction text, caution messages, and voice status
#supports keyboard navigation (n/b keys) and external voice command polling via file system
#minimal dark transparent panel with color-coded text for optimal visibility in 3d viewport

#procedural steps for central line placement procedure
#nine sequential steps from patient verification through final placement confirmation
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

#safety caution messages corresponding one-to-one with each procedural step
#each caution reinforces critical safety points specific to that step stage
cautions = [
    "Maintain sterile field at all times.",
    "Confirm probe orientation and vessel identity before proceeding.",
    "Do not confuse artery and vein; verify compressibility carefully.",
    "Maintain continuous needle tip visualization.",
    "Do not advance if access is uncertain.",
    "Advance guidewire only after confirmed venous entry.",
    "Avoid excessive force during dilation.",
    "Do not advance catheter beyond intended depth.",
    "Confirm placement and monitor for complications."
]

#global variables tracking current procedure step and voice command file path
#current step ranges from 0 to 8 and determines which instruction and caution display
currentStep = 0
COMMAND_FILE = "/tmp/slicer_voice_command.txt"

#access slicer 3d viewport components for rendering overlay elements
#obtains layout manager, 3d widget, render window, renderer, and interactor for event handling
layoutManager = slicer.app.layoutManager()
threeDWidget = layoutManager.threeDWidget(0)
view = threeDWidget.threeDView()
renderWindow = view.renderWindow()
renderer = renderWindow.GetRenderers().GetFirstRenderer()
interactor = view.interactor()

#remove previous overlay actors and observers when script reruns to prevent duplicates
#cleans up text actors, event observers, and timers from any prior execution
oldActorNames = [
    "cliPanelActor",
    "cliStepActor",
    "cliInstructionActor",
    "cliCautionActor",
    "cliVoiceStatusActor"
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

#helper functions for creating overlay visual elements in the 3d viewport
#maketestractor generates colored text with positioning; makepanelactor creates background rectangles
def makeTextActor(text, x, y, fontSize=20, bold=False, color=(1, 1, 1)):
    actor = vtk.vtkTextActor()
    actor.SetInput(text)

    prop = actor.GetTextProperty()
    prop.SetFontSize(fontSize)
    prop.SetBold(1 if bold else 0)
    prop.SetColor(*color)
    prop.SetJustificationToLeft()
    prop.SetVerticalJustificationToTop()

    actor.SetDisplayPosition(x, y)
    renderer.AddActor2D(actor)
    return actor

def makePanelActor(x, y, width, height, color=(0.08, 0.08, 0.12), opacity=0.55):
    points = vtk.vtkPoints()
    points.InsertNextPoint(x, y, 0)
    points.InsertNextPoint(x + width, y, 0)
    points.InsertNextPoint(x + width, y + height, 0)
    points.InsertNextPoint(x, y + height, 0)

    polygon = vtk.vtkPolygon()
    polygon.GetPointIds().SetNumberOfIds(4)
    for i in range(4):
        polygon.GetPointIds().SetId(i, i)

    polygons = vtk.vtkCellArray()
    polygons.InsertNextCell(polygon)

    polyData = vtk.vtkPolyData()
    polyData.SetPoints(points)
    polyData.SetPolys(polygons)

    mapper = vtk.vtkPolyDataMapper2D()
    mapper.SetInputData(polyData)

    actor = vtk.vtkActor2D()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetOpacity(opacity)

    renderer.AddActor2D(actor)
    return actor

#pixel coordinates and dimensions for hud panel and text element positioning
#panel provides dark background; text elements positioned within panel from top to bottom
PANEL_X = 20
PANEL_Y = 20
PANEL_W = 760
PANEL_H = 180

STEP_X = 40
STEP_Y = 170

INSTR_X = 40
INSTR_Y = 130

CAUTION_X = 40
CAUTION_Y = 82

VOICE_X = 40
VOICE_Y = 38

#instantiate all hud visual elements: dark background panel and four text layers
#step number in yellow, instruction in white, caution in red, voice status in light blue
panelActor = makePanelActor(
    PANEL_X, PANEL_Y, PANEL_W, PANEL_H,
    color=(0.08, 0.08, 0.12), opacity=0.55
)

stepActor = makeTextActor(
    "",
    STEP_X, STEP_Y,
    fontSize=24,
    bold=True,
    color=(1.0, 0.95, 0.15)
)

instructionActor = makeTextActor(
    "",
    INSTR_X, INSTR_Y,
    fontSize=22,
    bold=False,
    color=(1, 1, 1)
)

cautionActor = makeTextActor(
    "",
    CAUTION_X, CAUTION_Y,
    fontSize=18,
    bold=True,
    color=(1.0, 0.45, 0.45)
)

voiceStatusActor = makeTextActor(
    "Voice: waiting for external commands",
    VOICE_X, VOICE_Y,
    fontSize=14,
    bold=False,
    color=(0.70, 0.90, 1.0)
)

#store all actors as slicer module attributes for cleanup and access on subsequent script reruns
slicer.cliPanelActor = panelActor
slicer.cliStepActor = stepActor
slicer.cliInstructionActor = instructionActor
slicer.cliCautionActor = cautionActor
slicer.cliVoiceStatusActor = voiceStatusActor

#functions to refresh hud display content based on current procedure step
#updatehud reflects current step and instruction; setvoicestatus shows voice feedback messages
def updateHUD():
    global currentStep

    stepActor.SetInput(f"STEP {currentStep + 1} / {len(steps)}")
    instructionActor.SetInput(steps[currentStep])
    cautionActor.SetInput(f"CAUTION: {cautions[currentStep]}")
    renderWindow.Render()

def setVoiceStatus(text):
    voiceStatusActor.SetInput(text)
    renderWindow.Render()

#step navigation functions for advancing to next step or going back one step
#updates current step index, refreshes hud display, and logs navigation action to console
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
    print(f"BACK -> Step {currentStep + 1}: {steps[currentStep]}")

#expose navigation functions to slicer module for manual console testing when needed
slicer.cliNextStep = nextStep
slicer.cliPrevStep = prevStep

#keyboard event handler for n and b key presses to control step navigation
#n advances to next step, b goes back one step; observer attached to 3d viewport
def onKeyPress(caller, event):
    key = interactor.GetKeySym()
    if not key:
        return

    key = key.lower()

    if key == "n":
        nextStep()
    elif key == "b" or key == "p":
        prevStep()

keyPressObserverTag = interactor.AddObserver("KeyPressEvent", onKeyPress)
slicer.cliKeyPressObserverTag = keyPressObserverTag

#periodic polling of external voice command file for next/back commands from voice system
#checks command file every 500ms; parses command and removes file on read to avoid duplicate processing
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

        elif cmd == "back" or cmd == "prev":
            setVoiceStatus("Voice heard: BACK")
            prevStep()

        else:
            setVoiceStatus(f"Voice heard: ignored ({cmd})")

    except Exception as e:
        setVoiceStatus("Voice read error")
        print("Voice read error:", e)

voiceTimer = qt.QTimer()
voiceTimer.timeout.connect(checkVoiceCommand)
voiceTimer.start(500)

slicer.cliVoiceTimer = voiceTimer

#initialize viewport camera and display first step of procedure
#starts voice command polling timer and confirms system ready via console output
renderer.ResetCamera()
updateHUD()

print("Clean instruction overlay ready.")
print("Controls:")
print("  Press N for next")
print("  Press B for back")
print("  Manual test: slicer.cliNextStep() or slicer.cliPrevStep()")
print("  External voice polling active")
print(f"  Watching command file: {COMMAND_FILE}")
