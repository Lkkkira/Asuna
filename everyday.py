"""Offline task management, bounded arithmetic and common unit conversion."""
import ast
import copy
import math
import operator
import re
from datetime import date


class TaskService:
    def __init__(self,actions):
        self.actions = actions

    def commit(self,value):
        previous = self.actions.state
        self.actions.state = value
        try:
            self.actions.save()
        except OSError:
            self.actions.state = previous
            raise

    def add(self,text):
        text = text.strip()
        if not text or len(text)>4000:
            raise ValueError('A task needs 1–4,000 characters.')
        value = copy.deepcopy(self.actions.state)
        number = max([t['id'] for t in value['tasks']],default=0)+1
        value['tasks'].append({'id':number,'text':text,'done':False,'archived':False,'priority':'normal','due':''})
        self.commit(value)
        return f'Added task {number}: {text}'

    def edit(self,number,changes):
        if type(number) is not int or not isinstance(changes,dict) or not changes or set(changes)-{'text','done','archived','priority','due'}:
            raise ValueError('Choose a task and valid text, status, priority or due date.')
        value = copy.deepcopy(self.actions.state)
        task = next((t for t in value['tasks'] if t['id']==number),None)
        if task is None:
            raise ValueError('Task number not found. Ask to show tasks.')
        for field,entry in changes.items():
            if field=='text' and (not isinstance(entry,str) or not entry.strip() or len(entry)>4000):
                raise ValueError('Task text needs 1–4,000 characters.')
            if field in ('done','archived') and type(entry) is not bool:
                raise ValueError('Task status must be enabled or disabled.')
            if field=='priority' and entry not in ('low','normal','high'):
                raise ValueError('Choose low, normal or high priority.')
            if field=='due':
                if not isinstance(entry,str):
                    raise ValueError('Use YYYY-MM-DD for the due date, or leave it blank.')
                if entry and date.fromisoformat(entry).isoformat()!=entry:
                    raise ValueError('Use YYYY-MM-DD for the due date.')
            task[field] = entry.strip() if field=='text' else entry
        self.commit(value)
        return f"Updated task {number}: {task['text']}"

    def listing(self,include_archived=False):
        tasks = [t for t in self.actions.state['tasks'] if include_archived or not t.get('archived',False)]
        return '\n'.join(f"{t['id']}. {'[archived]' if t.get('archived') else '[done]' if t['done'] else '[open]'} {t['text']}"+
                         (f" • due {t['due']}" if t.get('due') else '')+f" • {t.get('priority','normal')}" for t in tasks) or 'No tasks yet. Try: add task: finish something'


def calculate(expression):
    if not expression.strip() or len(expression)>300:
        raise ValueError('Enter an arithmetic expression up to 300 characters.')
    try:
        tree = ast.parse(expression.replace('^','**'),mode='eval')
    except SyntaxError:
        raise ValueError('Use ordinary arithmetic, for example (12 + 3) * 4.') from None
    if sum(1 for _ in ast.walk(tree))>100:
        raise ValueError('This calculation is too complex.')
    binary = {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,
              ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod,ast.Pow:operator.pow}
    functions = {'sqrt':math.sqrt,'sin':math.sin,'cos':math.cos,'tan':math.tan,'log':math.log,
                 'log10':math.log10,'abs':abs,'round':round,'min':min,'max':max}
    constants = {'pi':math.pi,'e':math.e,'tau':math.tau}

    def evaluate(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            result = float(node.value)
        elif isinstance(node,ast.Name) and node.id in constants:
            result = constants[node.id]
        elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            result = evaluate(node.operand)*(1 if isinstance(node.op,ast.UAdd) else -1)
        elif isinstance(node,ast.BinOp) and type(node.op) in binary:
            left,right = evaluate(node.left),evaluate(node.right)
            if isinstance(node.op,ast.Pow) and abs(right)>500:
                raise ValueError('The exponent is too large.')
            result = binary[type(node.op)](left,right)
        elif isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in functions and not node.keywords and 1<=len(node.args)<=10:
            args = [evaluate(n) for n in node.args]
            if node.func.id=='round' and len(args)==2:
                if args[1]!=int(args[1]) or abs(args[1])>20:
                    raise ValueError('Choose a rounding precision from -20 to 20.')
                args[1] = int(args[1])
            result = functions[node.func.id](*args)
        else:
            raise ValueError('Only arithmetic and sqrt/sin/cos/tan/log/log10/abs/round/min/max are supported.')
        if isinstance(result,complex) or not math.isfinite(result) or abs(result)>1e100:
            raise ValueError('The result is outside the supported range.')
        return result

    try:
        result = evaluate(tree.body)
    except (ZeroDivisionError,OverflowError,TypeError) as exc:
        raise ValueError('The calculation is undefined or outside the supported range.') from exc
    return expression.strip()+' = '+format(result,'.12g')


UNITS = {
    'mm':('length',.001),'cm':('length',.01),'m':('length',1),'km':('length',1000),
    'in':('length',.0254),'ft':('length',.3048),'yd':('length',.9144),'mi':('length',1609.344),
    'g':('mass',.001),'kg':('mass',1),'oz':('mass',.028349523125),'lb':('mass',.45359237),
    's':('time',1),'min':('time',60),'h':('time',3600),'day':('time',86400),
    'b':('storage',1),'kb':('storage',1000),'mb':('storage',1000**2),'gb':('storage',1000**3),
    'kib':('storage',1024),'mib':('storage',1024**2),'gib':('storage',1024**3)}
ALIASES = {'meter':'m','meters':'m','metre':'m','metres':'m','kilometer':'km','kilometers':'km',
           'kilometre':'km','kilometres':'km','inch':'in','inches':'in','feet':'ft','foot':'ft',
           'mile':'mi','miles':'mi','gram':'g','grams':'g','kilogram':'kg','kilograms':'kg',
           'pound':'lb','pounds':'lb','lbs':'lb','second':'s','seconds':'s','minute':'min','minutes':'min',
           'hour':'h','hours':'h','days':'day','celsius':'c','fahrenheit':'f','kelvin':'k'}


def convert_units(text):
    match = re.fullmatch(r'\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?)\s*([a-z]+)\s+(?:to|in)\s+([a-z]+)\s*',text,re.I)
    if not match:
        raise ValueError('Try: convert 5 km to miles, or convert 30 c to f.')
    value = float(match[1])
    source,target = [ALIASES.get(u.lower(),u.lower()) for u in (match[2],match[3])]
    if not math.isfinite(value) or abs(value)>1e100:
        raise ValueError('Choose a finite value within the supported range.')
    if source in ('c','f','k') and target in ('c','f','k'):
        c = value if source=='c' else (value-32)*5/9 if source=='f' else value-273.15
        if c < -273.15-1e-9:
            raise ValueError('Temperature is below absolute zero.')
        result = c if target=='c' else c*9/5+32 if target=='f' else c+273.15
    elif source in UNITS and target in UNITS and UNITS[source][0]==UNITS[target][0]:
        result = value*UNITS[source][1]/UNITS[target][1]
    else:
        raise ValueError('Use compatible length, mass, time, temperature or byte-storage units. Currency needs current exchange-rate information.')
    return f'{value:g} {source} = {result:.12g} {target}'
