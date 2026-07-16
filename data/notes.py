def save_notes():
    global notes_box
    print("Saving notes...")

    try:
        with open("notes.txt", "w") as f:
            f.write(notes_box.get("1.0", "end-1c"))
    except Exception as e:
            print(e)