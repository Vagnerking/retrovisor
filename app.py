import argparse
import os
import sys

import threading
import time

try:
    import numpy as np
except ModuleNotFoundError:
    np = None
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
    TARGET_LABEL = 1

    def __init__(
        self,
        camera_index: int,
        width: int,
        height: int,
        margin: int,
        fps: int,
        reference_image: str,
        reference_dirs: list[str],
        similarity_threshold: float,
        match_distance_threshold: float,
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
        self.match_distance_threshold = max(1.0, match_distance_threshold)

        self.face_detector = self.cv2.CascadeClassifier(
            self.cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if self.face_detector.empty():
            raise RuntimeError("Não foi possível carregar o detector de rosto do OpenCV.")

        self.recognizer = self._create_recognizer()
        self.reference_faces_data: list = []
        self.reference_image_paths: list[str] = []

        self.alarm = AlarmPlayer()
        self.alarm_muted_until = 0.0
        self.alarm_active = False

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

        add_folder_button = tk.Button(
            controls,
            text="Adicionar pasta",
            command=self.select_reference_folder,
            bg="#1E5D3A",
            fg="white",
            activebackground="#2C7A4E",
            activeforeground="white",
            relief="flat",
            padx=8,
            pady=5,
        )
        add_folder_button.pack(side="right", padx=(0, 8), pady=6)

        select_photo_button = tk.Button(
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
        select_photo_button.pack(side="right", padx=(0, 8), pady=6)

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

        loaded_count, errors = self.set_reference_sources(reference_image, reference_dirs)
        if loaded_count == 0:
            self.status_var.set("Sem referência: use 'Selecionar foto' ou 'Adicionar pasta'")
            if errors:
                messagebox.showwarning("Referências não carregadas", "\n".join(errors[:4]))

        self.update_frame()

    def _create_recognizer(self):
        if not hasattr(self.cv2, "face") or not hasattr(self.cv2.face, "LBPHFaceRecognizer_create"):
            raise RuntimeError(
                "Reconhecimento LBPH indisponível. Instale: pip install opencv-contrib-python"
            )
        return self.cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)

    def _resolve_reference_path(self, path_value: str) -> str:
        if os.path.isabs(path_value):
            return path_value

        candidates = [
            os.path.join(os.getcwd(), path_value),
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), path_value),
            os.path.join(os.path.dirname(os.path.abspath(sys.executable)), path_value),
        ]

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        return os.path.join(os.getcwd(), path_value)

    def _normalize_face(self, gray_face):
        normalized = self.cv2.resize(gray_face, (160, 160), interpolation=self.cv2.INTER_AREA)
        normalized = self.cv2.equalizeHist(normalized)
        return normalized

    def _detect_faces(self, gray_frame):
        return self.face_detector.detectMultiScale(
            gray_frame,
            scaleFactor=1.08,
            minNeighbors=6,
            minSize=(40, 40),
        )

    def _extract_face_from_image(self, image_path: str):
        reference = self.cv2.imread(image_path)
        if reference is None:
            raise RuntimeError(f"Não foi possível abrir a imagem de referência: {image_path}.")

        gray = self.cv2.cvtColor(reference, self.cv2.COLOR_BGR2GRAY)
        faces = self._detect_faces(gray)
        if len(faces) == 0:
            raise RuntimeError(f"A imagem '{os.path.basename(image_path)}' não possui rosto detectável.")

        x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
        face = gray[y : y + h, x : x + w]
        return self._normalize_face(face)

    def _collect_images_from_dir(self, dir_path: str) -> list[str]:
        if not os.path.isdir(dir_path):
            raise RuntimeError(f"Pasta de referência não encontrada: {dir_path}")

        allowed_ext = {".jpg", ".jpeg", ".png", ".bmp"}
        files = []
        for name in sorted(os.listdir(dir_path)):
            ext = os.path.splitext(name)[1].lower()
            if ext in allowed_ext:
                files.append(os.path.join(dir_path, name))

        if not files:
            raise RuntimeError(f"A pasta '{dir_path}' não possui imagens compatíveis.")

        return files

    def _load_references_from_image(self, image_path: str) -> tuple[list, list[str], list[str]]:
        resolved_path = self._resolve_reference_path(image_path)
        if not os.path.exists(resolved_path):
            return [], [], [f"Imagem de referência não encontrada: {image_path}."]

        try:
            face = self._extract_face_from_image(resolved_path)
            return [face], [resolved_path], []
        except RuntimeError as error:
            return [], [], [str(error)]

    def _load_references_from_directory(self, dir_path: str) -> tuple[list, list[str], list[str]]:
        resolved_dir = self._resolve_reference_path(dir_path)
        try:
            image_paths = self._collect_images_from_dir(resolved_dir)
        except RuntimeError as error:
            return [], [], [str(error)]

        faces = []
        loaded_paths = []
        errors = []
        for path in image_paths:
            try:
                faces.append(self._extract_face_from_image(path))
                loaded_paths.append(path)
            except RuntimeError as error:
                errors.append(str(error))

        if not faces:
            errors.append(f"Nenhuma imagem válida com rosto foi carregada em: {resolved_dir}")

        return faces, loaded_paths, errors

    def _set_reference_dataset(self, faces_data: list, image_paths: list[str]) -> None:
        self.reference_faces_data = faces_data
        self.reference_image_paths = image_paths

        if not self.reference_faces_data:
            self.alarm.stop()
            self.alarm_active = False
            self.recognizer = self._create_recognizer()
            return

        labels = [self.TARGET_LABEL] * len(self.reference_faces_data)
        if np is not None:
            labels = np.array(labels, dtype="int32")
        self.recognizer = self._create_recognizer()
        self.recognizer.train(self.reference_faces_data, labels)

    def set_reference_sources(self, reference_image: str, reference_dirs: list[str]) -> tuple[int, list[str]]:
        all_faces = []
        all_paths = []
        all_errors = []

        if reference_image:
            faces, paths, errors = self._load_references_from_image(reference_image)
            all_faces.extend(faces)
            all_paths.extend(paths)
            all_errors.extend(errors)

        for dir_value in reference_dirs:
            faces, paths, errors = self._load_references_from_directory(dir_value)
            all_faces.extend(faces)
            all_paths.extend(paths)
            all_errors.extend(errors)

        self._set_reference_dataset(all_faces, all_paths)
        if self.reference_faces_data:
            self.status_var.set(f"{len(self.reference_faces_data)} referência(s) carregada(s).")
            return len(self.reference_faces_data), all_errors

        return 0, all_errors

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

        loaded, errors = self.set_reference_sources(selected_path, [])
        if loaded > 0:
            self.status_var.set(f"Referência atualizada ({loaded}). Monitorando...")
        elif errors:
            messagebox.showerror("Erro na foto de referência", "\n".join(errors[:3]))

    def select_reference_folder(self) -> None:
        selected_dir = filedialog.askdirectory(title="Selecione a pasta com imagens de referência")
        if not selected_dir:
            return

        faces, paths, errors = self._load_references_from_directory(selected_dir)
        merged_faces = self.reference_faces_data + faces
        merged_paths = self.reference_image_paths + paths

        if faces:
            self._set_reference_dataset(merged_faces, merged_paths)
            self.status_var.set(f"{len(self.reference_faces_data)} referência(s) carregada(s).")

        if errors and not faces:
            messagebox.showerror("Erro na pasta de referência", "\n".join(errors[:3]))

    def _predict_similarity(self, face_roi_gray) -> tuple[float, float]:
        if not self.reference_faces_data:
            return 0.0, 9999.0

        normalized = self._normalize_face(face_roi_gray)
        predicted_label, distance = self.recognizer.predict(normalized)
        distance = float(distance)

        if predicted_label != self.TARGET_LABEL:
            return 0.0, distance

        similarity = 1.0 - (distance / self.match_distance_threshold)
        similarity = max(0.0, min(1.0, similarity))
        return similarity, distance

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

            if not self.reference_faces_data:
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
                faces = self._detect_faces(gray)
                best_similarity = 0.0

                for (x, y, w, h) in faces:
                    roi_gray = gray[y : y + h, x : x + w]
                    similarity, distance = self._predict_similarity(roi_gray)
                    best_similarity = max(best_similarity, similarity)

                    color = (0, 0, 255) if similarity >= self.similarity_threshold else (255, 160, 0)
                    self.cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    self.cv2.putText(
                        frame,
                        f"{similarity * 100:.0f}% d={distance:.1f}",
                        (x, max(20, y - 8)),
                        self.cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
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
                        self.status_var.set(f"Monitorando ({len(self.reference_faces_data)} referência(s))...")

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
        help="Caminho da foto de referência principal (padrão: referencia.jpg).",
    )
    parser.add_argument(
        "--reference-dir",
        action="append",
        default=[],
        help="Pasta com imagens de referência (.jpg/.jpeg/.png/.bmp). Pode repetir o parâmetro.",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.5,
        help="Limiar de semelhança para disparar alarme (0.0 a 1.0, padrão: 0.5).",
    )
    parser.add_argument(
        "--match-distance-threshold",
        type=float,
        default=65.0,
        help="Limite de distância LBPH (quanto menor, mais rigoroso). Padrão: 65.",
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
            reference_dirs=args.reference_dir,
            similarity_threshold=max(0.0, min(1.0, args.similarity_threshold)),
            match_distance_threshold=max(1.0, args.match_distance_threshold),
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
