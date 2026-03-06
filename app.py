import argparse
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox


class AlarmPlayer:
    def __init__(self) -> None:
        self._running = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._alarm_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()

    def _alarm_loop(self) -> None:
        try:
            import winsound

            while self._running.is_set():
                winsound.Beep(1800, 250)
                time.sleep(0.2)
                winsound.Beep(1400, 250)
                time.sleep(0.3)
        except Exception:
            while self._running.is_set():
                print("\a", end="", flush=True)
                time.sleep(0.8)


class WebcamOverlayApp:
    def __init__(
        self,
        camera_index: int,
        width: int,
        height: int,
        margin: int,
        fps: int,
        reference_image: str,
        similarity_threshold: float,
    ) -> None:
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
        self.similarity_threshold = similarity_threshold

        self.face_detector = self.cv2.CascadeClassifier(
            self.cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if self.face_detector.empty():
            raise RuntimeError("Não foi possível carregar o detector de rosto do OpenCV.")

        self.alarm = AlarmPlayer()
        self.alarm_muted_until = 0.0
        self.alarm_active = False
        self.reference_face = None
        self.reference_image_path: str | None = None

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

        controls = tk.Frame(self.root, bg="#111111")
        controls.pack(fill="x", side="bottom")

        self.status_var = tk.StringVar(value="Monitorando...")
        status_label = tk.Label(
            controls,
            textvariable=self.status_var,
            bg="#111111",
            fg="white",
            anchor="w",
            padx=8,
        )
        status_label.pack(side="left", fill="x", expand=True)

        self.select_reference_button = tk.Button(
            controls,
            text="Selecionar foto",
            command=self.select_reference_image,
            bg="#1C4D7A",
            fg="white",
            activebackground="#2A689F",
            activeforeground="white",
            relief="flat",
            padx=8,
            pady=5,
        )
        self.select_reference_button.pack(side="right", padx=(0, 8), pady=6)

        mute_button = tk.Button(
            controls,
            text="Parar alarme (30s)",
            command=self.mute_alarm_for_30s,
            bg="#7A1A1A",
            fg="white",
            activebackground="#9E2626",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=5,
        )
        mute_button.pack(side="right", padx=8, pady=6)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Escape>", lambda _event: self.on_close())

        loaded, error = self.set_reference_image(reference_image)
        if not loaded:
            self.status_var.set("Sem referência: clique em 'Selecionar foto'")
            if error:
                messagebox.showwarning(
                    "Foto de referência não carregada",
                    (
                        f"{error}\n\n"
                        "A webcam continuará aberta. Clique em 'Selecionar foto' para configurar a referência."
                    ),
                )

        self.update_frame()

    def _resolve_reference_image_path(self, image_path: str) -> str:
        if os.path.isabs(image_path):
            return image_path

        candidates = [
            os.path.join(os.getcwd(), image_path),
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), image_path),
            os.path.join(os.path.dirname(os.path.abspath(sys.executable)), image_path),
        ]

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        return os.path.join(os.getcwd(), image_path)

    def _load_reference_face(self, image_path: str):
        resolved_path = self._resolve_reference_image_path(image_path)
        if not os.path.exists(resolved_path):
            raise RuntimeError(
                f"Imagem de referência não encontrada: {image_path}."
            )

        reference = self.cv2.imread(resolved_path)
        if reference is None:
            raise RuntimeError(
                f"Não foi possível abrir a imagem de referência: {resolved_path}."
            )

        gray = self.cv2.cvtColor(reference, self.cv2.COLOR_BGR2GRAY)
        faces = self.face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        if len(faces) == 0:
            raise RuntimeError(
                "A imagem de referência não possui um rosto detectável. "
                "Use uma foto frontal e bem iluminada."
            )

        x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
        face = gray[y : y + h, x : x + w]
        return self.cv2.resize(face, (100, 100), interpolation=self.cv2.INTER_AREA), resolved_path

    def set_reference_image(self, image_path: str) -> tuple[bool, str | None]:
        try:
            face, resolved_path = self._load_reference_face(image_path)
        except RuntimeError as error:
            self.reference_face = None
            self.reference_image_path = None
            self.alarm.stop()
            self.alarm_active = False
            return False, str(error)

        self.reference_face = face
        self.reference_image_path = resolved_path
        self.status_var.set("Referência carregada. Monitorando...")
        return True, None

    def select_reference_image(self) -> None:
        selected_path = filedialog.askopenfilename(
            title="Selecione a foto de referência",
            filetypes=[
                ("Imagens", "*.jpg *.jpeg *.png *.bmp"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not selected_path:
            return

        loaded, error = self.set_reference_image(selected_path)
        if loaded:
            self.status_var.set("Referência atualizada. Monitorando...")
        elif error:
            messagebox.showerror("Erro na foto de referência", error)

    def _calculate_similarity(self, face_roi_gray) -> float:
        candidate = self.cv2.resize(face_roi_gray, (100, 100), interpolation=self.cv2.INTER_AREA)
        result = self.cv2.matchTemplate(
            candidate,
            self.reference_face,
            self.cv2.TM_CCOEFF_NORMED,
        )
        similarity = float(result[0][0])
        return max(0.0, min(1.0, similarity))

    def mute_alarm_for_30s(self) -> None:
        self.alarm_muted_until = time.time() + 30
        self.alarm.stop()
        self.alarm_active = False
        self.status_var.set("Alarme pausado por 30 segundos")

    def update_frame(self) -> None:
        ok, frame = self.cap.read()
        if ok:
            frame = self.cv2.resize(frame, (self.width, self.height), interpolation=self.cv2.INTER_AREA)
            gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)

            if self.reference_face is None:
                self.alarm.stop()
                self.alarm_active = False
                self.cv2.putText(
                    frame,
                    "Sem referencia",
                    (10, 30),
                    self.cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                )
            else:
                faces = self.face_detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=6)
                best_similarity = 0.0
                for (x, y, w, h) in faces:
                    roi_gray = gray[y : y + h, x : x + w]
                    similarity = self._calculate_similarity(roi_gray)
                    best_similarity = max(best_similarity, similarity)

                    color = (0, 0, 255) if similarity >= self.similarity_threshold else (255, 160, 0)
                    self.cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    self.cv2.putText(
                        frame,
                        f"{similarity * 100:.0f}%",
                        (x, max(20, y - 8)),
                        self.cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        color,
                        2,
                    )

                now = time.time()
                has_match = best_similarity >= self.similarity_threshold
                is_muted = now < self.alarm_muted_until

                if has_match and not is_muted:
                    if not self.alarm_active:
                        self.alarm.start()
                        self.alarm_active = True
                    self.status_var.set(f"ALERTA! Semelhança: {best_similarity * 100:.0f}%")
                else:
                    if self.alarm_active:
                        self.alarm.stop()
                        self.alarm_active = False
                    if is_muted:
                        remaining = int(self.alarm_muted_until - now)
                        self.status_var.set(f"Alarme pausado ({remaining}s)")
                    else:
                        self.status_var.set("Monitorando...")

            frame = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
            image = self.Image.fromarray(frame)
            image_tk = self.ImageTk.PhotoImage(image=image)
            self.label.image_tk = image_tk
            self.label.configure(image=image_tk)

        self.root.after(self.delay, self.update_frame)

    def on_close(self) -> None:
        self.alarm.stop()
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
    parser.add_argument(
        "--reference-image",
        default="referencia.jpg",
        help="Caminho da foto de referência da pessoa que deve disparar o alarme (padrão: referencia.jpg).",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.5,
        help="Limiar de semelhança para disparar alarme (0.0 a 1.0, padrão: 0.5).",
    )
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
            reference_image=args.reference_image,
            similarity_threshold=max(0.0, min(1.0, args.similarity_threshold)),
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
