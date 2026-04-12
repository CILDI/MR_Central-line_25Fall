import speech_recognition as sr

COMMAND_FILE = "/tmp/slicer_voice_command.txt"

recognizer = sr.Recognizer()
mic = sr.Microphone()

print("Voice control ready.")
print("Say: next or previous")

while True:
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source)

        text = recognizer.recognize_google(audio).lower()

        print("Heard:", text)

        if "next" in text:
            with open(COMMAND_FILE, "w") as f:
                f.write("next")

        elif "previous" in text or "back" in text:
            with open(COMMAND_FILE, "w") as f:
                f.write("prev")

    except sr.UnknownValueError:
        pass