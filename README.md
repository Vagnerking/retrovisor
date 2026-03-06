# Vigia Webcam (Top Right)

Aplicativo simples em Python para deixar a sua webcam **sempre visível no canto superior direito da tela**.

Ideal para você ver quem está chegando por trás sem precisar virar toda hora.

## Requisitos

- Python 3.10+
- Webcam funcionando

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Como executar

```bash
python app.py
```

### Opções úteis

```bash
python app.py --camera-index 0 --width 420 --height 240 --margin 20 --fps 24
```

- `--camera-index`: troque para `1`, `2`, etc. caso tenha mais de uma câmera.
- `--width` e `--height`: tamanho da janelinha.
- `--margin`: distância do topo e da direita.
- `--fps`: velocidade de atualização.

## Gerar `.exe` no Windows

No Windows, rode:

```bat
build_windows_exe.bat
```

Ao final, o executável estará em:

```text
dist\VigiaWebcam.exe
```

> Observação: para gerar `.exe`, o build precisa ser feito em ambiente Windows.

## Controles

- A janela abre sempre no topo (`always on top`).
- Pressione `Esc` para fechar rapidamente.
- Também pode fechar pelo `X` da janela.

## Dicas

- Se a webcam não abrir, feche apps que já estejam usando câmera (Zoom, Teams, OBS etc.).
- No Linux, pode ser necessário conceder permissão de câmera ao ambiente gráfico.
