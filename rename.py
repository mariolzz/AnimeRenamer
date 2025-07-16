import os
import re
import logging
import argparse

# --- CONFIGURAZIONE GLOBALE ---
# Lista dei formati video da elaborare. È possibile aggiungere o rimuovere estensioni qui.
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm')


def setup_console_logging():
    """
    Imposta un logger semplice che scrive solo sulla console.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
    )


def clean_filename(filename: str) -> str:
    """
    Applica una serie di regole di pulizia a un nome di file.
    Rimuove i tag, formatta gli spazi e gestisce i trattini per standardizzare i nomi.

    Args:
        filename (str): Il nome del file originale (con estensione).

    Returns:
        str: Il nuovo nome del file, pulito secondo le regole.
    """
    # Separa il nome del file dalla sua estensione per evitare di modificarla
    name, ext = os.path.splitext(filename)
    
    # Rimuove gli indicatori di versione come "v2", "V3" etc. attaccati agli episodi.
    name = re.sub(r'(S\d+E\d+|E\d+|S\d+)(v\d+)', r'\1', name, flags=re.IGNORECASE)
    
    # Rimuove ricorsivamente i tag come [Subs] o (1080p) dall'inizio o dalla fine del nome
    while True:
        stripped_name = name.strip()
        pattern = r"^\s*(\[.*?\]|\(.*?\))\s*|\s*(\[.*?\]|\(.*?\))\s*$"
        name = re.sub(pattern, '', stripped_name)
        # Se non vengono apportate ulteriori modifiche, esce dal ciclo
        if name == stripped_name:
            break
            
    # Sostituisce gli underscore, spesso usati al posto degli spazi
    name = name.replace('_', ' ')
    
    # Sostituisce i punti con spazi, ma solo se non sono seguiti da un numero.
    # In questo modo "Ver1.1a" e "S01E18.5" sono protetti, ma "Serie.S01" viene corretto.
    name = re.sub(r'\.(?!\d)', ' ', name)
    
    # --- Gestione intelligente dei trattini ---
    
    # --- MODIFICA CHIAVE QUI ---
    # Aggiorniamo i pattern per riconoscere numeri decimali come "18.5".
    # Il pattern per un numero diventa \d+(?:\.\d+)? che significa "cifre seguite opzionalmente da un punto e altre cifre".
    
    # Pattern per l'identificativo dell'episodio (S01, Episode 50, Movie 01, S01E18.5 etc.)
    EPISODE_ID_PATTERN = r'(?:S|E|Ep(?:isode)?\.?|Movie)\s*\d+(?:\.\d+)?'

    # Pattern per i trattini seguiti solo da numeri (es. "Yuru Yuri - 01" o "Serie - 01.5")
    SIMPLE_NUMERIC_ID_PATTERN = r'\d+(?:\.\d+)?'

    # Combinazione dei pattern in un'unica espressione per il lookahead,
    # per proteggere qualsiasi ID da una modifica errata.
    ANY_ID_PATTERN = f'(?:{EPISODE_ID_PATTERN}|{SIMPLE_NUMERIC_ID_PATTERN})'

    # 1. Aggiunge spazi per i separatori di episodio (es. "Serie-S01" -> "Serie - S01")
    name = re.sub(
        r'\s*-\s*(' + EPISODE_ID_PATTERN + r')', 
        r' - \1', 
        name, 
        flags=re.IGNORECASE
    )
    
    # 2. Rimuove gli spazi attorno ai trattini che uniscono parole (es. "hanako - kun"),
    #    ma lascia intatti i separatori di titolo/episodio.
    name = re.sub(
        r'(?<=[a-zA-Z])\s+-\s+(?!' + ANY_ID_PATTERN + r')(?=[a-zA-Z])', 
        '-', 
        name,
        flags=re.IGNORECASE
    )

    # Pulisce eventuali doppi spazi creati e rifila gli spazi iniziali/finali
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Riassembla il nome finale con la sua estensione originale
    return f"{name}{ext}"


def process_directory(root_dir: str, dry_run: bool = True):
    """
    Analizza ricorsivamente una directory e rinomina solo i file video.
    Applica le regole di `clean_filename` a ogni file video trovato.

    Args:
        root_dir (str): Il percorso della directory da cui iniziare la scansione.
        dry_run (bool): Se True, simula solo le operazioni senza modificare alcun file.
    """
    if dry_run:
        logging.warning("--- ESECUZIONE IN MODALITÀ DRY-RUN (SIMULAZIONE) ---")
        logging.info(f"Verranno cercati solo i file con queste estensioni: {VIDEO_EXTENSIONS}")
        logging.warning("Nessun file sarà rinominato. Usa --force per applicare le modifiche.")
    else:
        logging.info("--- AVVIO ELABORAZIONE REALE ---")
        logging.info(f"Elaborazione dei soli file con estensioni: {VIDEO_EXTENSIONS}")
        
    counters = {'processed_videos': 0, 'to_rename': 0, 'skipped_other_files': 0, 'errors': 0}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Esclude le directory nascoste (es. .git)
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]

        for filename in filenames:
            is_video = filename.lower().endswith(VIDEO_EXTENSIONS)
            
            # Salta i file nascosti o che non sono video
            if filename.startswith('.') or not is_video:
                counters['skipped_other_files'] += 1
                continue

            counters['processed_videos'] += 1
            old_filepath = os.path.join(dirpath, filename)
            
            try:
                new_filename = clean_filename(filename)
                
                # Se il nome è già corretto, passa al file successivo
                if filename == new_filename:
                    continue
                
                counters['to_rename'] += 1
                
                logging.info(f"[{'DRY-RUN' if dry_run else 'RINOMINA'}]")
                logging.info(f"  Vecchio: {filename}")
                logging.info(f"  Nuovo: {new_filename}")
                
                if not dry_run:
                    new_filepath = os.path.join(dirpath, new_filename)
                    if os.path.exists(new_filepath):
                        logging.error(f"  -> ERRORE: Il file '{new_filename}' esiste già. Salto.")
                        counters['errors'] += 1
                        counters['to_rename'] -= 1
                    else:
                        os.rename(old_filepath, new_filepath)

            except Exception as e:
                logging.error(f"  -> ERRORE INASPETTATO su {old_filepath}: {e}")
                counters['errors'] += 1
                if counters['to_rename'] > 0: counters['to_rename'] -= 1

    logging.info("--- ELABORAZIONE COMPLETATA ---")
    unchanged_videos = counters['processed_videos'] - counters['to_rename'] - counters['errors']
    
    if dry_run:
        logging.info(f"File video analizzati: {counters['processed_videos']}")
        logging.info(f"File che verrebbero rinominati: {counters['to_rename']}")
        logging.info(f"File video già corretti: {unchanged_videos}")
    else:
        actually_renamed = counters['to_rename']
        logging.info(f"File video effettivamente rinominati: {actually_renamed}")
        logging.info(f"File video non modificati: {unchanged_videos}")
    
    logging.info(f"File totali ignorati (non video, di sistema): {counters['skipped_other_files']}")
    if counters['errors'] > 0:
        logging.warning(f"Errori riscontrati: {counters['errors']}")


if __name__ == "__main__":
    setup_console_logging()

    parser = argparse.ArgumentParser(
        description="Rinomina i file video di anime. Per impostazione predefinita, viene eseguito in modalità di simulazione.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("directory", nargs='?', default=os.getcwd(), help="Opzionale: il percorso da analizzare. Se omesso, usa la directory corrente.")
    
    parser.add_argument("--force", action="store_true", help="Esegue la rinomina effettiva dei file. USARE CON CAUTELA.")

    args = parser.parse_args()
    
    is_dry_run = not args.force
    
    process_directory(args.directory, dry_run=is_dry_run)
