"""Short action acknowledgements; detailed tool output belongs in the work view."""
import re


def short_text(value,limit=120):
    value = re.sub(r'\s+',' ',value).strip()
    return value if len(value)<=limit else value[:limit].rsplit(' ',1)[0]+'…'


def brief_error(value):
    """Do not narrate a diagnostic page/control dump appended to an error."""
    for line in str(value).splitlines():
        line = line.strip()
        if line and not re.match(r'(?:Page:|https?://|\d+\.\s*\[(?:button|link|field)\])',line,re.I):
            return short_text(line,300)
    return 'The action could not be completed. Details are in Activity.'


def browser_feedback(tool,text,number,detail):
    """Return the chat acknowledgement and optional different speech text."""
    if tool=='browser_read':
        return detail,'Page read. The page text and controls are available in chat and Activity.'
    if tool=='browser_tabs':
        return detail,'Your browser tabs are listed in chat and Activity.'
    if tool=='browser_open_item':
        order = {1:'first',2:'second',3:'third',4:'fourth',5:'fifth'}.get(number,str(number))
        return f'Opened the {order} {text}.',None
    if tool=='browser_media':
        state = detail.casefold()
        if text=='play':
            message = 'The player is still paused.' if 'media state: paused' in state else 'Playing it now.'
        elif text=='pause':
            message = 'The player is still playing.' if 'media state: playing' in state else 'Paused.'
        elif text=='mute':
            message = 'The player is still unmuted.' if 'unmuted' in state else 'Muted.'
        else:
            message = 'The player is still muted.' if 'muted' in state and 'unmuted' not in state else 'Sound is on.'
        return message,None
    if tool=='browser_click':
        if detail.startswith(('Liked the video','This video is already liked')):
            return detail.splitlines()[0],None
        return 'Used the selected page control.',None
    if tool=='browser_fill':return 'Entered the text. It has not been submitted.',None
    if tool=='browser_search':return 'Submitted the website search.',None
    messages = {'browser_back':'Went back.','browser_forward':'Went forward.','browser_reload':'Reloaded the page.',
                'browser_scroll':'Scrolled '+text+'.','browser_find':'Found the text on the page.',
                'browser_switch_tab':f'Switched to tab {number}.'}
    return messages.get(tool,'Browser action completed.'),None


def completion_feedback(steps,replies,speech):
    # Search -> choose first video -> play is one user request, with one final acknowledgement.
    if ([s['tool'] for s in steps]==['search_youtube','browser_open_item','browser_media'] and
            steps[1]['text']=='video' and steps[1]['number']==1 and steps[2]['text']=='play' and
            replies[-1]=='Playing it now.'):
        message = 'Playing '+short_text(steps[0]['text'])+' on YouTube.'
        return message,message
    return '\n\n'.join(replies),'\n\n'.join(part for part in speech if part)
