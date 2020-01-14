import pickle
import sys

def main():
    pickle_filename = sys.argv[1]
    full_notes_contents = None
    with open(pickle_filename, 'rb') as file:
        full_notes_contents = pickle.load(file)

    output_filename_template = 'note_{}.txt'
    for i, note in enumerate(full_notes_contents):
        output_filename = output_filename_template.format(i)
        with open(output_filename, 'wb') as out_file:
            out_file.write(note.encode('utf-8'))

if __name__ == '__main__':
    main()
