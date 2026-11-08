"""OS-held file lock prevents two ASUNA processes writing the same local state."""
from pathlib import Path


class SingleInstance:
    def __init__(self,data):
        self.path = Path(data)/'asuna.lock'
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.handle = self.path.open('a+b')
        if self.path.stat().st_size==0:
            self.handle.write(b'0')
            self.handle.flush()
        self.handle.seek(0)
        try:
            import msvcrt
            msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
        except ImportError:
            import fcntl
            try:
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:
                self.handle.close()
                raise RuntimeError('ASUNA is already running. Use the existing window or close it before starting another.') from None
        except OSError:
            self.handle.close()
            raise RuntimeError('ASUNA is already running. Use the existing window or close it before starting another.') from None
        return self

    def __exit__(self,*args):
        if self.handle and not self.handle.closed:
            self.handle.seek(0)
            try:
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1)
            except ImportError:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
            finally:
                self.handle.close()
