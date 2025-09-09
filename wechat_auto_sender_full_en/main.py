from scheduler import start_scheduler
from db_utils import init_db
if __name__=='__main__':
    init_db(); start_scheduler(); input('Running... Press Enter to exit')
