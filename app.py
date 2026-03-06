import argparse
import sys
import tkinter as tk
from tkinter import messagebox


class WebcamOverlayApp:
    def __init__(self, camera_index: int, width: int, height: int, margin: int, fps: int) -> None:
        import cv2
        from PIL import Image, ImageTk

        self.cv2 = cv2
        self.Image = Image
        self.ImageTk = ImageTk

        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.margin = margin
        self.delay = max(1, int(1000 / max(1, fps)))

        self.cap = self.cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Não foi possível abrir a webcam no índice {self.camera_index}. "
                "Verifique permissões e se outra aplicação já está usando a câmera."
            )

        self.root = tk.Tk()
        self.root.title("Vigia Webcam")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        screen_width = self.root.winfo_screenwidth()
        x = max(0, screen_width - self.width - self.margin)
        y = max(0, self.margin)

        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.configure(bg="black")

        self.label = tk.Label(self.root, bg="black")
        self.label.pack(fill="both", expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Escape>", lambda _event: self.on_close())

        self.update_frame()

    def update_frame(self) -> None:
        ok, frame = self.cap.read()
        if ok:
            frame = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
            frame = self.cv2.resize(frame, (self.width, self.height), interpolation=self.cv2.INTER_AREA)
            image = self.Image.fromarray(frame)
            image_tk = self.ImageTk.PhotoImage(image=image)
            self.label.image_tk = image_tk
            self.label.configure(image=image_tk)

        self.root.after(self.delay, self.update_frame)

    def on_close(self) -> None:
        if self.cap:
            self.cap.release()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Abre uma janela sempre no topo, no canto superior direito, "
            "exibindo a imagem da sua webcam."
        )
    )
    parser.add_argument("--camera-index", type=int, default=0, help="Índice da webcam (padrão: 0).")
    parser.add_argument("--width", type=int, default=420, help="Largura da janela (padrão: 420).")
    parser.add_argument("--height", type=int, default=240, help="Altura da janela (padrão: 240).")
    parser.add_argument("--margin", type=int, default=20, help="Margem do topo/direita (padrão: 20).")
    parser.add_argument("--fps", type=int, default=24, help="FPS alvo para atualização (padrão: 24).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        app = WebcamOverlayApp(
            camera_index=args.camera_index,
            width=args.width,
            height=args.height,
            margin=args.margin,
            fps=args.fps,
        )
        app.run()
    except ModuleNotFoundError as error:
        missing_module = error.name or "dependência"
        print(
            f"Dependência ausente: {missing_module}. Instale com: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1
    except RuntimeError as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erro ao abrir webcam", str(error))
        root.destroy()
        return 1
    except Exception as error:
        print(f"Erro inesperado: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
