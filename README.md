# Vigia Webcam (Top Right)

Aplicativo em Python para deixar a webcam **sempre visível no canto superior direito da tela**, com detecção facial e alarme.

## Requisitos

- Python 3.10+
- Webcam funcionando
- Foto de referência da pessoa que deve disparar o alarme (ex.: `referencia.jpg`)

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Como executar

```bash
python app.py --reference-image referencia.jpg
```

### Opções úteis

```bash
python app.py --camera-index 0 --width 420 --height 240 --margin 20 --fps 24 --reference-image referencia.jpg --similarity-threshold 0.5
```

- `--camera-index`: troque para `1`, `2`, etc. caso tenha mais de uma câmera.
- `--width` e `--height`: tamanho da janela.
- `--margin`: distância do topo e da direita.
- `--fps`: velocidade de atualização.
- `--reference-image`: foto usada como referência para comparação facial.
- `--similarity-threshold`: nível de semelhança para disparar o alarme (`0.5` = 50%).

## Funcionamento do alarme

- Quando um rosto for detectado com semelhança igual ou maior que o limite configurado (padrão 50%), o alarme toca.
- O botão **"Parar alarme (30s)"** pausa o alarme por 30 segundos.
- Durante a pausa, o alarme não toca.
- Após os 30 segundos, se o rosto for detectado novamente acima do limite, o alarme volta a tocar.

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

- Use uma foto de referência frontal e bem iluminada para melhorar a detecção.
- Se a webcam não abrir, feche apps que já estejam usando câmera (Zoom, Teams, OBS etc.).
- Esta detecção usa comparação simples por OpenCV, então pode haver falsos positivos/negativos em ambientes difíceis.
