# Vigia Webcam (Top Right)

Aplicativo em Python para deixar a webcam **sempre visível no canto superior direito da tela**, com detecção facial e alarme.

## Requisitos

- Python 3.10+
- Webcam funcionando
- Foto(s) de referência da pessoa que deve disparar o alarme

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

### Várias pastas de referência

Você pode passar várias pastas para o app carregar **todas as imagens** dessas pastas (`.jpg/.jpeg/.png/.bmp`):

```bash
python app.py --reference-dir refs_casa --reference-dir refs_trabalho --similarity-threshold 0.5
```

### Opções úteis

```bash
python app.py --camera-index 0 --width 420 --height 240 --margin 20 --fps 24 --reference-image referencia.jpg --reference-dir minhas_referencias --similarity-threshold 0.5
```

- `--camera-index`: troque para `1`, `2`, etc. caso tenha mais de uma câmera.
- `--width` e `--height`: tamanho da janela.
- `--margin`: distância do topo e da direita.
- `--fps`: velocidade de atualização.
- `--reference-image`: foto de referência principal.
- `--reference-dir`: pasta com várias imagens de referência (pode repetir esse parâmetro).
- `--similarity-threshold`: nível de semelhança para disparar o alarme (`0.5` = 50%).

## Funcionamento do alarme

- Quando um rosto for detectado com semelhança igual ou maior que o limite configurado (padrão 50%), o alarme toca.
- O botão **"Parar alarme (30s)"** pausa o alarme por 30 segundos.
- Durante a pausa, o alarme não toca.
- Após os 30 segundos, se o rosto for detectado novamente acima do limite, o alarme volta a tocar.

## Carregar referências em tempo real

- **Selecionar foto**: substitui as referências atuais por uma foto escolhida.
- **Adicionar pasta**: adiciona todas as imagens válidas da pasta às referências já carregadas.

## Foto de referência no `.exe`

- O app tenta localizar arquivos relativos em:
  1. pasta atual,
  2. pasta do script/executável.
- Se não encontrar referências válidas, o app **não fecha**: ele abre normalmente e mostra aviso.

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

- Use fotos de referência frontais e bem iluminadas para melhorar a detecção.
- Se a webcam não abrir, feche apps que já estejam usando câmera (Zoom, Teams, OBS etc.).
- Esta detecção usa comparação simples por OpenCV, então pode haver falsos positivos/negativos em ambientes difíceis.
