import argparse
from pathlib import Path
from database.backup import restore_database
p=argparse.ArgumentParser(); p.add_argument('backup'); p.add_argument('--confirm',required=True); a=p.parse_args(); restore_database(Path(a.backup),a.confirm); print('База восстановлена')
