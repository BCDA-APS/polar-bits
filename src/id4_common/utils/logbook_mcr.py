# For APS logbook shift events
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import re
from html.parser import HTMLParser


class ShiftEventParser(HTMLParser):
    """Parser to extract shift events from HTML."""
    
    def __init__(self):
        super().__init__()
        self.events = []
        self.in_shift_events = False
        self.in_paragraph = False
        self.current_text = ""
        self.found_shift_events_header = False
    
    def handle_starttag(self, tag, attrs):
        if tag == "h2" and not self.found_shift_events_header:
            # Check if next content is "3. Shift Events"
            pass
        elif tag == "p" and self.in_shift_events:
            self.in_paragraph = True
            self.current_text = ""
        elif tag == "br" and self.in_paragraph:
            # Use newline as separator so events within a <p> can be split later
            self.current_text += "\n"
    
    def handle_endtag(self, tag):
        if tag == "p" and self.in_paragraph:
            self.in_paragraph = False
            current_event = None
            for line in self.current_text.split("\n"):
                text = re.sub(r'[ \t]+', ' ', line.strip())
                if not text:
                    continue
                match = re.match(r'(\d{2}:\d{2})\s*-\s*(.*)', text)
                if match:
                    if current_event:
                        self.events.append(current_event)
                    time, description = match.groups()
                    current_event = (time, description.strip())
                elif current_event:
                    # Continuation of the previous event's description
                    t, desc = current_event
                    current_event = (t, (desc + " " + text).strip())
            if current_event:
                self.events.append(current_event)
    
    def handle_data(self, data):
        if self.in_shift_events:
            # Check if we've reached the next section
            if re.match(r'^\s*\d+\.\s+\w+', data) and self.events:
                self.in_shift_events = False
                return
            
            if self.in_paragraph:
                self.current_text += data
        
        # Look for "3. Shift Events" to start parsing
        if not self.found_shift_events_header and "3. Shift Events" in data:
            self.found_shift_events_header = True
            self.in_shift_events = True
    
    def handle_entityref(self, name):
        """Handle HTML entities like &nbsp; &amp; etc."""
        if self.in_paragraph:
            # Convert common entities to their text equivalents
            entities = {
                'nbsp': ' ',
                'amp': '&',
                'lt': '<',
                'gt': '>',
                'quot': '"',
                'apos': "'"
            }
            self.current_text += entities.get(name, f'&{name};')
    
    def handle_charref(self, name):
        """Handle numeric character references like &#160;"""
        if self.in_paragraph:
            try:
                if name.startswith('x'):
                    char = chr(int(name[1:], 16))
                else:
                    char = chr(int(name))
                self.current_text += char
            except (ValueError, OverflowError):
                self.current_text += f'&#{name};'


def _get_logbook_url():
    """
    Construct the logbook URL based on current day and time.
    Shifts are 6 AM - 6 PM (0600-1800) and 6 PM - 6 AM next day (1800-0600).
    """
    now = datetime.now()
    year = now.strftime("%Y")  # YYYY format
    month = now.strftime("%m")  # MM format
    day = now.strftime("%d")    # DD format
    year_short = now.strftime("%y")  # YY format for date string
    
    # Determine which shift we're in
    hour = now.hour
    if hour >= 6 and hour < 18:
        # Morning shift: 6 AM - 6 PM
        shift_time = "0600-1800"
        date_str = f"{year_short}{month}{day}"
    else:
        # Evening shift: 6 PM - 6 AM (next day)
        shift_time = "1800-0600"
        if hour >= 18:
            # Still in today's evening shift
            date_str = f"{year_short}{month}{day}"
        else:
            # In the morning, but this is the previous day's evening shift
            yesterday = now - timedelta(days=1)
            date_str = yesterday.strftime(f"{year_short}{month}%d")
    
    year_month = f"{year}{month}"
    url = f"https://www.aps4.anl.gov/operations/ops_log/{year_month}_archive/{date_str}_{shift_time}.shtml"
    return url


def _extract_shift_events(html_content, n=3):
    """
    Extract the shift events section from the HTML content
    and return the last n entries.
    
    Args:
        html_content: The HTML content to parse
        n: Number of events to return (default: 3)
    """
    parser = ShiftEventParser()
    try:
        parser.feed(html_content)
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return []
    
    if not parser.events:
        return []
    
    # Return the last n events in reverse chronological order (newest first)
    return parser.events[-n:][::-1]


def fetch_shift_events(n=3):
    """
    Fetch and display the last n shift events from the APS logbook.
    
    Parameters
    ----------
    n : int
        Number of shift events to display (default: 3)
    
    Returns
    -------
    list
        List of tuples containing (time, description) for each event
    """
    if n < 1:
        print("Error: Number of events must be at least 1")
        return []
    
    url = _get_logbook_url()
    print(f"Fetching logbook from: {url}\n")
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            html_content = response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        print(f"Error fetching the webpage: HTTP {e.code}")
        return []
    except urllib.error.URLError as e:
        print(f"Error fetching the webpage: {e}")
        return []
    except Exception as e:
        print(f"Error fetching the webpage: {e}")
        return []
    
    events = _extract_shift_events(html_content, n=n)
    
    if not events:
        print("No shift events found")
        return []
    
    print(f"Last {len(events)} Shift Events:")
    print("=" * 70)
    for i, (time, description) in enumerate(events, 1):
        print(f"{i}. {time} - {description}\n")
    
    #return events

