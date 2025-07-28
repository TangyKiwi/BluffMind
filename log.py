global LOGFILE

LOGFILE = None
PRINT_CONSOLE = False

def log_start(filename, print_console=False):
    global LOGFILE
    LOGFILE = open(filename, "w")
    global PRINT_CONSOLE
    PRINT_CONSOLE = print_console

def log_message(message: str):
    global LOGFILE
    if LOGFILE is None:
        log_start()
    LOGFILE.write(message + "\n")
    LOGFILE.flush()
    if PRINT_CONSOLE:
        print(message + "\n")
    
def log_end():
    global LOGFILE
    if LOGFILE:
        LOGFILE.close()
        LOGFILE = None
    