# Schach Coach (Chess Coach)

A small Windows tool for chess beginners. Take a screenshot of your game, and the program reads the position, lets **Stockfish** calculate the best moves, and explains what to play and why. It is especially meant for learning checkmates (e.g. the ladder mate) and avoiding stalemate.

> **Note:** The program's interface and the coach's explanations are in **German**.

## How it works

1. Take a screenshot of the board (Windows: `Win+Shift+S`, it goes to the clipboard)
2. Claude reads the pieces from the image
3. You confirm or correct the detected position
4. Stockfish calculates the top 3 moves (including "mate in X")
5. Claude explains the situation, the best move and typical mistakes to avoid

## Setup

Requirements: Windows, Python 3.10+

1. Download this repository
2. Download [Stockfish](https://stockfishchess.org/download/) and unzip it.
   Put the folder or the `stockfish...exe` next to `schach_coach.py`. The program finds it automatically.
3. Create an API key in the [Claude Console](https://platform.claude.com/settings/keys).
   **Heads up:** The API is paid (pay-as-you-go) and separate from a Claude chat subscription. A single analysis costs only a few cents.
4. Start `schach_coach.py` by double-clicking it (or run `python schach_coach.py`).
   On first start it asks for your key and stores it in `api_key.txt`.
   Missing Python packages are installed automatically (see `requirements.txt`).

Alternatively, set the key as the environment variable `ANTHROPIC_API_KEY`.

## Usage

- At startup, choose White or Black.
- Press `Win+Shift+S`, select the board, then press **Enter** in the program window.
- `f` switches your color, `q` quits.

## Notes and limitations

- Reading the position from a screenshot is done by an AI model and can make mistakes (e.g. mixed-up pieces). That is why the detected board is shown before the analysis. Please double-check it.
- Castling rights and en passant are not detected; the analysis assumes no castling.
- **Never share your `api_key.txt`.** It is listed in `.gitignore`.

## License

MIT, see `LICENSE`. Stockfish is a separate program under the GPL and is not part of this repository.
