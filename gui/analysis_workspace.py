import customtkinter as ctk
from PIL import Image


PIECE_PATH = "../assets/pieces/"


def load_piece(filename):
    from io import BytesIO
    import cairosvg

    png_data = cairosvg.svg2png(
        url=PIECE_PATH + filename,
        output_width=70,
        output_height=70
    )

    image = Image.open(BytesIO(png_data))

    return ctk.CTkImage(
        light_image=image,
        dark_image=image,
        size=(70, 70)
    )


def show_analysis_preview():

    app = ctk.CTk()
    app.configure(fg_color="#172134")

    app.title("Chess Analysis Preview")
    app.geometry("700x700")

    title = ctk.CTkLabel(
        app,
        text="Analysis Workspace Preview",
        font=("Arial", 24),
        text_color="white"
    )

    title.pack(pady=20)

    board_frame = ctk.CTkFrame(
        app,
        fg_color="#172134"
    )

    board_frame.pack()

    pieces = [
        ["br.svg", "bn.svg", "bb.svg", "bq.svg",
         "bk.svg", "bb.svg", "bn.svg", "br.svg"],

        ["bp.svg"] * 8,

        [""] * 8,
        [""] * 8,
        [""] * 8,
        [""] * 8,

        ["wp.svg"] * 8,

        ["wr.svg", "wn.svg", "wb.svg", "wq.svg",
         "wk.svg", "wb.svg", "wn.svg", "wr.svg"]
    ]


    for row in range(8):
        for col in range(8):

            square_color = "#9f7939" if (row + col) % 2 else "#fbcba4"

            square = ctk.CTkFrame(
                board_frame,
                width=70,
                height=70,
                fg_color=square_color,
                corner_radius=0
            )

            square.grid(
                row=row,
                column=col,
                padx=0,
                pady=0
            )

            square.grid_propagate(False)

            piece = pieces[row][col]

            if piece:
                img = load_piece(piece)

                label = ctk.CTkLabel(
                    square,
                    text="",
                    image=img
                )

                label.image = img
                label.pack(expand=True)


    app.mainloop()


show_analysis_preview()