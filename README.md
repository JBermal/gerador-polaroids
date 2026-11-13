# Gerador de Polaroids

Aplicativo desktop (Windows) para transformar fotos em Polaroid, 3×4, 5×7 ou formato personalizado, com dimensões físicas precisas para impressão.

Distribuído como executável compilado com [Nuitka](https://nuitka.net/). Código-fonte e scripts de build ficam neste repositório.

## Download

Baixe o executável em [`dist_nuitka/`](https://github.com/JBermal/gerador-polaroids/tree/main/dist_nuitka) ou pela [release](https://github.com/JBermal/gerador-polaroids/releases) — não é necessário instalar Python.

## Recursos

- Presets: Polaroid (6,5 × 8,5 cm), 3×4 cm e 5×7 cm
- Formato personalizado (largura, altura, margens e DPI)
- Processamento em lote (até 50 imagens)
- Legenda automática pelo nome do arquivo ou texto customizado
- Saída em JPEG com metadados DPI para impressão
- Opção de sombra na moldura

## Estrutura do projeto

```
polaroid/
├── polaroid_gui.py      # Interface gráfica (PyQt6)
├── photo_engine.py      # Motor de processamento (Pillow)
├── assets/              # Ícone e logo embutidos no build
├── dist_nuitka/         # Executável Windows pronto (~25 MB)
├── onefile_nuitka.bat   # Compilação onefile (Nuitka)
├── release_sign.ps1     # Assinatura e checksum do .exe
├── requirements.txt     # Dependências de execução
└── requirements-build.txt
```

## Executar a partir do código

Requisitos: Python 3.10+ (recomendado 3.11–3.13) no Windows.

```bash
python -m venv .bancada
.bancada\Scripts\activate
pip install -r requirements.txt
python polaroid_gui.py
```

## Compilar o executável

1. Instale as dependências de build (inclui Nuitka):

```bash
pip install -r requirements-build.txt
```

2. Garanta `assets/logo.png` e `assets/logo.ico` (o `.bat` gera o `.ico` a partir do PNG se faltar).

3. Compile:

```bash
onefile_nuitka.bat
```

O binário sai em `dist_nuitka/`.

4. (Opcional) Assinar e gerar SHA-256:

```powershell
powershell -ExecutionPolicy Bypass -File .\release_sign.ps1
```

## Uso rápido do app

1. Abra o Gerador de Polaroids
2. Selecione o preset ou ajuste o formato
3. Adicione as fotos
4. Escolha a pasta de saída (padrão: pasta Imagens do Windows)
5. Gere as imagens

## Formatos de entrada

JPEG, PNG, BMP e TIFF.

## Licença

MIT — veja [LICENSE](LICENSE).
