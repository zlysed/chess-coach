"""
Schach-Coach zum Doppelklicken.

Ablauf: Win+Shift+S -> Brett ausschneiden -> im Fenster Enter drücken ->
Stellung wird erkannt, Stockfish rechnet, Claude erklärt auf Deutsch.

Einrichtung (einmalig):
  - stockfish.exe (oder ein Ordner mit stockfish...exe) in DENSELBEN Ordner wie diese Datei legen
  - beim ersten Start wird nach dem API-Key gefragt und in api_key.txt gespeichert
  - fehlende Python-Pakete werden automatisch installiert
"""
import importlib.util
import os
import subprocess
import sys
import traceback

ORDNER = os.path.dirname(os.path.abspath(__file__))
os.chdir(ORDNER)

# --- fehlende Pakete automatisch installieren ---
_BENOETIGT = {"anthropic": "anthropic", "chess": "python-chess", "PIL": "pillow"}
_fehlend = [pip for mod, pip in _BENOETIGT.items() if importlib.util.find_spec(mod) is None]
if _fehlend:
    print("Installiere fehlende Pakete:", ", ".join(_fehlend), "...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", *_fehlend])

import base64
import glob
import io
import re
import shutil

import anthropic
import chess
import chess.engine
from PIL import Image, ImageGrab

MODEL = "claude-sonnet-5-5"
KEY_DATEI = os.path.join(ORDNER, "api_key.txt")


def hole_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key.strip()
    if os.path.exists(KEY_DATEI):
        with open(KEY_DATEI, encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            return key
    print("Noch kein API-Key gespeichert (erstellen auf console.anthropic.com).")
    key = input("API-Key hier einfügen: ").strip()
    with open(KEY_DATEI, "w", encoding="utf-8") as f:
        f.write(key)
    print("Gespeichert in api_key.txt (gib diese Datei niemandem).")
    return key


def finde_stockfish():
    treffer = glob.glob(os.path.join(ORDNER, "**", "stockfish*.exe"), recursive=True)
    if treffer:
        return treffer[0]
    return os.environ.get("STOCKFISH_PATH") or shutil.which("stockfish")


def lade_bild():
    img = ImageGrab.grabclipboard()
    if isinstance(img, list) and img:
        img = Image.open(img[0])
    if not isinstance(img, Image.Image):
        raise RuntimeError("Kein Bild in der Zwischenablage. Erst Win+Shift+S drücken und das Brett ausschneiden.")
    img = img.convert("RGB")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


def frage_claude(client, bild_b64, text):
    antwort = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": bild_b64}},
                {"type": "text", "text": text},
            ],
        }],
    )
    return "".join(b.text for b in antwort.content if b.type == "text")


def lese_stellung(client, bild_b64, farbe_de):
    prompt = f"""Das ist ein Screenshot eines Schachbretts. Lies die Stellung ab.
Gehe Reihe für Reihe vor und nenne für jede der 8 Reihen alle Figuren mit Feld
(z. B. "Reihe 3: weißer Turm d3, weißer Bauer e3, weißer König f3").
Nutze die Koordinaten am Brettrand, falls vorhanden. Normalerweise sitzt {farbe_de} unten.
Achte auf Brettdrehung und lass keine Figur aus.
Gib ganz am Ende eine eigene Zeile im Format:
FEN: <nur der Figurenteil, z. B. 8/8/8/7P/2R5/3RPK2/8/k7>
Großbuchstaben = Weiß, Kleinbuchstaben = Schwarz."""
    text = frage_claude(client, bild_b64, prompt)
    treffer = re.findall(r"FEN:\s*([prnbqkPRNBQK1-8/]+)", text)
    return treffer[-1] if treffer else None


def analysiere(board, engine_pfad, zeit=1.5, anzahl=3):
    zeilen = []
    with chess.engine.SimpleEngine.popen_uci(engine_pfad) as engine:
        infos = engine.analyse(board, chess.engine.Limit(time=zeit), multipv=anzahl)
    for info in infos:
        zug = info["pv"][0]
        score = info["score"].pov(board.turn)
        if score.is_mate():
            m = score.mate()
            bewertung = f"Matt in {m}" if m > 0 else f"Matt gegen dich in {-m}"
        else:
            bewertung = f"{score.score() / 100:+.2f} Bauern"
        zeilen.append((board.san(zug), bewertung, board.variation_san(info["pv"][:6])))
    return zeilen


def eine_analyse(client, engine_pfad, farbe):
    farbe_de = "Weiß" if farbe == "w" else "Schwarz"
    print("\nLese Screenshot ...")
    bild = lade_bild()
    placement = lese_stellung(client, bild, farbe_de)

    while True:
        board = None
        if placement:
            try:
                b = chess.Board(f"{placement} {farbe} - - 0 1")
                if b.is_valid():
                    board = b
                    print("\nSo habe ich das Brett verstanden (Großbuchstaben = Weiß):\n")
                    print(board)
                else:
                    print("\nDie erkannte Stellung ist nicht gültig:", placement)
            except ValueError:
                print("\nKonnte die Stellung nicht lesen:", placement)
        eingabe = input("\nStimmt das? Enter = ja, oder korrigierten Figurenteil des FEN eintippen: ").strip()
        if eingabe:
            placement = eingabe
            continue
        if board:
            break
        print("Bitte gib die Stellung manuell ein.")

    if board.is_game_over():
        print("Die Partie ist schon vorbei:", board.result())
        return

    if engine_pfad:
        print("\nStockfish rechnet ...")
        top = analysiere(board, engine_pfad)
        print("\nBeste Züge:")
        for san, bew, folge in top:
            print(f"  {san:8} {bew:22} {folge}")
        engine_text = "\n".join(f"- {s} ({b}), Variante: {f}" for s, b, f in top)
    else:
        print("\n(Kein Stockfish gefunden. Leg stockfish.exe in den Ordner dieser Datei, dann wird es viel besser.)")
        engine_text = "(keine Engine-Analyse verfügbar)"

    prompt = f"""Stellung (FEN): {board.fen()}
Der Spieler hat {farbe_de} und ist am Zug. Er ist Anfänger und besonders schwach im Mattsetzen.

Stockfish-Analyse:
{engine_text}

Erkläre auf Deutsch, einfach und kurz:
1. Was ist die Lage (Material, Königssicherheit)?
2. Welchen Zug soll er spielen und warum? Falls ein Matt möglich ist, erkläre die Idee dahinter
   (z. B. Leitermatt, Grundreihenmatt) und worauf er achten muss, damit es kein Patt wird.
3. Welchen typischen Fehler sollte er hier vermeiden?
Nutze nur Züge aus der Stockfish-Analyse, erfinde keine eigenen."""
    erklaerung = client.messages.create(
        model=MODEL, max_tokens=1200, messages=[{"role": "user", "content": prompt}]
    )
    print("\n--- Coach ---\n")
    print("".join(b.text for b in erklaerung.content if b.type == "text"))


def main():
    print("=== Schach-Coach ===")
    client = anthropic.Anthropic(api_key=hole_api_key())
    engine_pfad = finde_stockfish()
    print("Stockfish:", engine_pfad if engine_pfad else "nicht gefunden")

    farbe = "w"
    antwort = input("Spielst du Weiß oder Schwarz? [w/s, Enter = Weiß]: ").strip().lower()
    if antwort.startswith("s"):
        farbe = "b"

    while True:
        wahl = input(
            "\nMach jetzt Win+Shift+S und schneide das Brett aus.\n"
            "Dann hier Enter = analysieren, f = Farbe wechseln, q = beenden: "
        ).strip().lower()
        if wahl == "q":
            break
        if wahl == "f":
            farbe = "b" if farbe == "w" else "w"
            print("Du spielst jetzt", "Weiß" if farbe == "w" else "Schwarz")
            continue
        try:
            eine_analyse(client, engine_pfad, farbe)
        except Exception as e:
            print("\nFehler:", e)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
    input("\nEnter zum Schließen ...")
