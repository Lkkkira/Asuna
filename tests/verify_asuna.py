import sys
import tempfile
import time
import zipfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from actions import Actions, read_document
import asuna

with tempfile.TemporaryDirectory() as folder:
    base = Path(folder).resolve()
    data = base / 'data'
    data.mkdir()
    scope = base / 'library'
    scope.mkdir()
    (scope / 'chapter.txt').write_text('Photosynthesis uses sunlight.', encoding='utf-8')
    (base / 'outside.txt').write_text('outside')
    a = Actions(data)
    assert 'Added task 1' in a.execute('ASUNA, please add task: study biology')
    assert 'Completed task 1' in a.execute('complete task 1')
    assert '[done]' in Actions(data).execute('show tasks')
    assert 'Choose a search folder' in a.execute('find file: chapter')
    a.choose_folder(scope)
    assert 'chapter.txt' in a.execute('find file: chapter')
    with patch('actions.os.startfile') as opened:
        a.execute('open result 1')
        opened.assert_called_once_with(str(scope / 'chapter.txt'))
    a.results = [base / 'outside.txt']
    with patch('actions.os.startfile') as opened:
        assert 'no longer available' in a.execute('open result 1')
        opened.assert_not_called()
    with patch('actions.subprocess.Popen') as launch:
        a.execute('Can you open paint')
        launch.assert_called_once_with(['mspaint.exe'], shell=False)
    with patch('actions.open_chrome') as browser:
        a.execute('search web for: photosynthesis & sunlight')
        assert 'photosynthesis+%26+sunlight' in browser.call_args[0][0]
    assert 'could not match' in a.execute('open unknown-program.exe')
    a.execute('remind me in 1 minute to stretch')
    a.state['reminders'][0]['due'] = (datetime.now() - timedelta(seconds=1)).isoformat()
    a.save()
    restarted = Actions(data)
    assert len(restarted.due()) == 1
    assert not Actions(data).due()
    a = Actions(data)
    a.execute('remind me in 5 minutes to drink water')
    assert 'Cancelled' in a.execute('cancel reminder 2')
    assert 'No pending' in a.execute('show reminders')
    assert read_document(scope / 'chapter.txt')[1] == 'Photosynthesis uses sunlight.'
    doc = scope / 'lesson.docx'
    with zipfile.ZipFile(doc, 'w') as z:
        z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello</w:t></w:r><w:r><w:t> world</w:t></w:r></w:p></w:body></w:document>')
    assert read_document(doc)[1] == 'Hello world'
    (scope / 'long.txt').write_text('a' * 12000)
    assert read_document(scope / 'long.txt')[2]

    asuna.DATA = data
    root = asuna.tk.Tk()
    root.withdraw()
    app = asuna.Asuna(root)
    app.submit('add task: UI task')
    deadline = time.monotonic() + 10
    while app.busy and time.monotonic() < deadline:
        root.update()
        time.sleep(.02)
    assert not app.busy
    assert 'UI task' in app.chat.get('1.0', 'end')
    assert (data / 'conversation.json').exists()
    app.show_activity(True)
    root.update()
    app.show_activity(False)
    app.document = read_document(doc)
    app.busy = True
    app.events.put(('begin', None))
    app.events.put(('token', 'Hello '))
    app.events.put(('token', 'there'))
    app.events.put(('done', ('hello', 'Hello there')))
    app.poll()
    assert 'Hello there' in app.chat.get('1.0', 'end')
    assert not app.busy
    app.clear()
    assert app.document is None
    assert 'UI task' in app.actions.execute('show tasks')
    root.destroy()
print('PASS: task persistence, reminder restart/cancel/once-only delivery, scoped file opening, app launch, web encoding, text/Word reading, document limits, async UI results, streaming, and new conversation.')
