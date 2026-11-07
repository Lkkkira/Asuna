"""Explicit local memories and recurring daily/weekly routines."""
import copy
import json
from datetime import datetime, timedelta


def validate_repeat(repeat):
    if not isinstance(repeat, dict) or set(repeat) != {'cadence', 'time', 'weekday', 'kind'}:
        raise ValueError('A routine needs cadence, time, weekday and kind.')
    if repeat['cadence'] not in ('daily', 'weekdays', 'weekly') or repeat['kind'] not in ('reminder', 'task'):
        raise ValueError('Supported routines: daily, weekdays, or weekly; reminders or tasks.')
    if type(repeat['weekday']) is not int or not 0 <= repeat['weekday'] <= 6:
        raise ValueError('Choose a weekday from Monday (0) to Sunday (6).')
    try:
        parsed = datetime.strptime(repeat['time'], '%H:%M')
    except (ValueError, TypeError):
        raise ValueError('Choose a routine time in 24-hour HH:MM format.') from None
    if parsed.strftime('%H:%M') != repeat['time']:
        raise ValueError('Use a two-digit hour and minute, such as 08:30.')
    return repeat


def next_occurrence(repeat, after):
    validate_repeat(repeat)
    hour, minute = map(int, repeat['time'].split(':'))
    for days in range(8):
        candidate = (after + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        allowed = (repeat['cadence'] == 'daily' or
                   repeat['cadence'] == 'weekdays' and candidate.weekday() < 5 or
                   repeat['cadence'] == 'weekly' and candidate.weekday() == repeat['weekday'])
        if allowed and candidate > after:
            return candidate
    raise ValueError('Could not find the next routine occurrence.')


def schedule_label(repeat):
    cadence = repeat['cadence']
    if cadence == 'weekly':
        cadence = 'every ' + ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')[repeat['weekday']]
    return cadence + ' at ' + repeat['time']


class PersonalStore:
    def __init__(self, data):
        self.path = data / 'personal.json'
        self.state = {'memories': [], 'routines': [], 'context_floor': 0}
        if self.path.exists():
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            if (not isinstance(saved, dict) or not {'memories', 'routines'} <= set(saved) or
                    any(not isinstance(saved[k], list) for k in ('memories', 'routines')) or
                    type(saved.get('context_floor', 0)) is not int or saved.get('context_floor', 0) < 0):
                raise ValueError('Personal data has an invalid format; restore it from a backup.')
            self.state.update(saved)

    def commit(self, changed):
        # Failed saves must not leave unsaved preferences/routines active in memory.
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(changed, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.path)
        self.state = changed

    def save_memory(self, text, number=0, context_floor=None):
        text = text.strip()
        if not text or len(text) > 1000:
            raise ValueError('A memory must contain 1–1,000 characters.')
        changed = copy.deepcopy(self.state)
        memories = changed['memories']
        if number:
            memory = next((m for m in memories if m['id'] == number and not m['archived']), None)
            if memory is None:
                raise ValueError('Active memory number not found. Ask to show memories.')
            memory['text'] = text
            if context_floor is not None:
                changed['context_floor'] = context_floor
        else:
            duplicate = next((m for m in memories if not m['archived'] and m['text'].casefold() == text.casefold()), None)
            if duplicate:
                return 'Already saved as memory ' + str(duplicate['id']) + ': ' + duplicate['text']
            memory = {'id': max([m['id'] for m in memories], default=0) + 1, 'text': text, 'archived': False}
            memories.append(memory)
        memory['updated_at'] = datetime.now().isoformat()
        self.commit(changed)
        return 'Saved memory ' + str(memory['id']) + ': ' + text

    def archive_memory(self, number, restore=False, context_floor=None):
        changed = copy.deepcopy(self.state)
        memory = next((m for m in changed['memories'] if m['id'] == number), None)
        if memory is None:
            raise ValueError('Memory number not found.')
        memory['archived'] = not restore
        if not restore and context_floor is not None:
            changed['context_floor'] = context_floor
        self.commit(changed)
        return ('Restored' if restore else 'Archived') + ' memory ' + str(number) + ('.' if restore else '. It will no longer be supplied to the model. Use restore memory ' + str(number) + ' to undo.')

    def reset_context(self):
        changed = copy.deepcopy(self.state)
        changed['context_floor'] = 0
        self.commit(changed)

    def memories(self, archived=False):
        return sorted((m.copy() for m in self.state['memories'] if m['archived'] == archived),
                      key=lambda m: (m['updated_at'], m['id']))

    def show_memories(self):
        active = '\n'.join(f"{m['id']}. {m['text']}" for m in self.memories()) or 'No saved memories.'
        archived = ', '.join(str(m['id']) for m in self.memories(True))
        return active + ('\n\nArchived memory IDs (not used in replies): ' + archived if archived else '')

    def add_routine(self, text, repeat, number=0, now=None):
        validate_repeat(repeat)
        text = text.strip()
        if not text or len(text) > 1000:
            raise ValueError('A routine needs a title of 1–1,000 characters.')
        now = now or datetime.now()
        changed = copy.deepcopy(self.state)
        routines = changed['routines']
        if number:
            routine = next((r for r in routines if r['id'] == number), None)
            if routine is None:
                raise ValueError('Routine number not found.')
        else:
            if any(r['active'] and r['text'].casefold() == text.casefold() and r['repeat'] == repeat for r in routines):
                return 'That routine is already active.'
            routine = {'id': max([r['id'] for r in routines], default=0) + 1}
            routines.append(routine)
        routine.update(text=text, repeat=repeat.copy(), active=True,
                       next_due=next_occurrence(repeat, now).isoformat(timespec='seconds'))
        self.commit(changed)
        return f"Saved routine {routine['id']}: {text}, {schedule_label(repeat)} ({repeat['kind']}). Next: {routine['next_due'].replace('T', ' ')}. Keep ASUNA open."

    def pause_routine(self, number, resume=False, now=None):
        changed = copy.deepcopy(self.state)
        routine = next((r for r in changed['routines'] if r['id'] == number), None)
        if routine is None:
            raise ValueError('Routine number not found.')
        routine['active'] = resume
        if resume:
            routine['next_due'] = next_occurrence(routine['repeat'], now or datetime.now()).isoformat(timespec='seconds')
        self.commit(changed)
        return ('Resumed' if resume else 'Paused') + ' routine ' + str(number) + '.'

    def show_routines(self):
        return '\n'.join(f"{r['id']}. {'[active]' if r['active'] else '[paused]'} {r['text']} — {schedule_label(r['repeat'])} ({r['repeat']['kind']}); next {r['next_due'].replace('T', ' ')}" for r in self.state['routines']) or 'No routines yet. Try: Remind me every day at 8 PM to stretch.'

    def due(self, now=None):
        now = now or datetime.now()
        return [copy.deepcopy(r) for r in self.state['routines'] if r['active'] and datetime.fromisoformat(r['next_due']) <= now]

    def acknowledge(self, number, expected_due, now=None):
        changed = copy.deepcopy(self.state)
        routine = next((r for r in changed['routines'] if r['id'] == number and r['active']), None)
        if routine is None or routine['next_due'] != expected_due:
            return
        routine['next_due'] = next_occurrence(routine['repeat'], now or datetime.now()).isoformat(timespec='seconds')
        self.commit(changed)

    def overview(self, actions, now=None):
        now = now or datetime.now()
        tasks = [t for t in actions.state['tasks'] if not t['done']]
        reminders = [r for r in actions.state['reminders'] if not r['delivered'] and datetime.fromisoformat(r['due']).date() <= now.date()]
        routines = [r for r in self.state['routines'] if r['active'] and datetime.fromisoformat(r['next_due']).date() <= now.date()]
        return ('Today — ' + now.strftime('%A, %d %B') + '\n\nOpen tasks (including undated):\n' +
                ('\n'.join(f"{t['id']}. {t['text']}" for t in tasks) or 'None.') +
                '\n\nOne-time reminders due today or overdue:\n' +
                ('\n'.join(f"{r['id']}. {r['due'].replace('T', ' ')} — {r['text']}" for r in reminders) or 'None.') +
                '\n\nRoutines due today or overdue:\n' +
                ('\n'.join(f"{r['id']}. {r['next_due'].replace('T', ' ')} — {r['text']} ({r['repeat']['kind']})" for r in routines) or 'None.'))
