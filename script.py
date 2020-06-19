import itertools
import pickle
import time

from com.dtmilano.android.viewclient import ViewClient

X_MAX = 1080
Y_MAX = 1920
X_MID = X_MAX // 2
Y_MID = Y_MAX // 2

REQUESTED_SCROLL_AMOUNT = None
SCROLL_DATA = []
NOTES_PREVIEWS = []
FULL_NOTES_CONTENTS = []

resource_id_base_ = 'com.miui.notes:id/'
resource_id_section_title = resource_id_base_ + 'section_title'
resource_id_preview = resource_id_base_ + 'preview'
resource_id_time = resource_id_base_ + 'time'
resource_id_note = resource_id_base_ + 'note'


def subelements_from_note_view(note_view):
    section_view, content_view, date_view = None, None, None

    for subelement in note_view.children:
        resource_id = subelement['resource-id']
        if resource_id_section_title == resource_id:
            section_view = subelement
        elif resource_id_note == resource_id:
            note = subelement
            for note_subelement in note.children:
                note_element_resource_id = note_subelement['resource-id']
                if resource_id_preview == note_element_resource_id:
                    content_view = note_subelement
                elif resource_id_time == note_element_resource_id:
                    date_view = note_subelement

    return section_view, content_view, date_view


def get_y_bounds(view):
    left_top, right_bottom = view.bounds()
    left, top = left_top
    right, bottom = right_bottom
    return top, bottom


def is_fully_visible(note_view):
    if len(note_view.children) < 1:
        return False
    first_subelement = note_view.children[0]
    last_subelement = note_view.children[-1]
    last_resource_id = last_subelement['resource-id']

    first_index_is_zero = (0 == int(first_subelement.index()))
    if not first_index_is_zero:
        return False
    last_item_is_a_note = (resource_id_note == last_resource_id)
    if not last_item_is_a_note:
        return False
    note = last_subelement
    last_subitem_contains_time = (resource_id_time == note.children[-1]['resource-id'])
    return last_subitem_contains_time


class Note:
    def __init__(self, content_view, date_view):
        self.content = content_view.text()
        self.date = date_view.text()

        _, bottom = get_y_bounds(content_view)
        self.midpoint = bottom

    @staticmethod
    def from_note_view(note_view):
        section_view, content_view, date_view = subelements_from_note_view(note_view)
        if content_view is None or date_view is None:
            return None
        return Note(content_view, date_view)


def are_notes_equivalent(note_1, note_2):
    is_eq_content = note_1.content == note_2.content
    is_eq_date = note_1.date == note_2.date
    return is_eq_content and is_eq_date


def find_scroll_delta(previous_note, current_note):
    current_y = current_note.midpoint
    previous_y = previous_note.midpoint
    scroll_delta = current_y - previous_y
    global SCROLL_DATA
    global REQUESTED_SCROLL_AMOUNT
    SCROLL_DATA.append((REQUESTED_SCROLL_AMOUNT, scroll_delta))
    return scroll_delta


def extract_notes_from_recycler_view(vc, most_recent_note=None, sleep_s=1.0):
    rich_editor_id = 'com.miui.notes:id/rich_editor'
    recycler_view_id = 'com.miui.notes:id/recycler_view'
    recycler_view = vc.findViewByIdOrRaise(recycler_view_id)

    start_index = 0  # iterate from first item by default
    fully_visible_note_views = list(itertools.ifilter(is_fully_visible, recycler_view.children))
    # If we scrolled, find the item which was at the end of the previous screen
    # (before scrolling). We have to skip all items leading up to and including
    # this one because they were already processed.
    if most_recent_note is not None:
        equivalent_index = find_equivalent_note_view_index(fully_visible_note_views, most_recent_note)
        start_index = equivalent_index + 1  # skip previous items

    note = None
    section_texts = []
    for note_view in fully_visible_note_views[start_index:]:
        # process note
        section_view, content_view, date_view = subelements_from_note_view(note_view)
        if section_view is not None:
            section_texts.append(section_view.text())
        note = Note(content_view, date_view)
        NOTES_PREVIEWS.append(note.content)

        # open note
        note_view.touch()
        vc.dump(window=-1, sleep=sleep_s)  # refresh view
        # extract text
        rich_editor = vc.findViewByIdOrRaise(rich_editor_id)
        full_note_contents = rich_editor.text()
        FULL_NOTES_CONTENTS.append(full_note_contents)
        # go back to the list of notes
        vc.findViewWithContentDescriptionOrRaise(u'Back').touch()
        vc.dump(window=-1, sleep=sleep_s)  # refresh view

    new_most_recent_note = note
    y_bounds_first = get_y_bounds(fully_visible_note_views[0])
    y_bounds_last = get_y_bounds(fully_visible_note_views[-1])
    y_bounds = y_bounds_first, y_bounds_last

    return y_bounds, section_texts, new_most_recent_note


def find_equivalent_note_view_index(fully_visible_note_views, target_note):
    """Find index of the note view whose note is equivalent to the given note."""

    def is_note_view_equivalent_to_target(note_view):
        return are_notes_equivalent(target_note, Note.from_note_view(note_view))

    equivalent_index, equivalent_note_view = next(
        (i, nv) for (i, nv) in enumerate(fully_visible_note_views)
        if is_note_view_equivalent_to_target(nv))
    # find out how much we actually scrolled
    equivalent_note = Note.from_note_view(equivalent_note_view)
    actual_scroll_delta = find_scroll_delta(target_note, equivalent_note)
    print 'actual_scroll_delta:', actual_scroll_delta
    return equivalent_index


def scroll_and_refresh(vc, y_from=1600, y_to=400, duration_ms=1000, sleep_s=1.0):
    """Scroll down for new items and refresh view data to reflect changes on the screen."""
    scroll_amount = y_to - y_from
    global REQUESTED_SCROLL_AMOUNT
    REQUESTED_SCROLL_AMOUNT = scroll_amount
    print 'scrolling from %d to %d (%d px)' % (y_from, y_to, scroll_amount)
    vc.device.drag((X_MID, y_from), (X_MID, y_to), duration_ms, steps=1, orientation=-1)
    vc.dump(window=-1, sleep=sleep_s)  # refresh view


def export_notes(vc):
    export_dir = 'exported_notes\\'
    sleep_s = 0

    swipe_duration_ms = 500
    overscroll_compensation_px = 50
    overscroll_compensation_factor = 1.2

    vc.dump(window=-1, sleep=sleep_s)  # refresh view

    most_recent_note = None
    sections = []
    while True:
        y_bounds, new_sections, most_recent_note = extract_notes_from_recycler_view(vc, most_recent_note, sleep_s)
        if len(new_sections) > 0:
            sections.extend(new_sections)

        if most_recent_note is None:
            # we are done, exit loop
            break

        y_bounds_first, y_bounds_last = y_bounds
        desired_scroll_amount = y_bounds_first[0] - y_bounds_last[0]
        desired_scroll_amount /= overscroll_compensation_factor
        scroll_to = 10
        scroll_from = scroll_to - desired_scroll_amount - overscroll_compensation_px
        scroll_and_refresh(vc, scroll_from, scroll_to, swipe_duration_ms, sleep_s)

    # save to file
    time_str = time.strftime("%Y-%m-%d_%H%M%S", time.gmtime())
    dump_filename = export_dir + 'notes.%s.pickle' % time_str
    with open(dump_filename, 'wb') as file_:
        pickle.dump(FULL_NOTES_CONTENTS, file_, pickle.HIGHEST_PROTOCOL)

    for s in sections:
        print s

    for requested, actual in SCROLL_DATA:
        ratio = float(actual) / requested
        delta = actual - requested
        print 'requested:', requested, 'ratio:', ratio, 'delta:', abs(delta)

    print
    print 'len(NOTES_PREVIEWS):', len(NOTES_PREVIEWS)
    for note_preview in NOTES_PREVIEWS:
        print note_preview.replace('\n', '_')
    print 'len(NOTES_PREVIEWS):', len(NOTES_PREVIEWS)


def main():
    # setup view client
    kwargs1 = {'ignoreversioncheck': False, 'verbose': False, 'ignoresecuredevice': False}
    device, serialno = ViewClient.connectToDeviceOrExit(**kwargs1)
    # start application on the device
    device.startActivity(component='com.miui.notes/com.miui.notes.ui.NotesListActivity')
    kwargs2 = {'forceviewserveruse': False, 'useuiautomatorhelper': False,
               'ignoreuiautomatorkilled': True, 'autodump': False, 'debug': {},
               'startviewserver': True, 'compresseddump': True}
    vc = ViewClient(device, serialno, **kwargs2)
    start = time.time()
    export_notes(vc)
    stop = time.time()
    print 'time:', stop - start


if __name__ == '__main__':
    main()
