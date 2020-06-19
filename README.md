# Extract MIUI Notes

This repository contains scripts used to extract notes from the MIUI Notes application distributed with the Android-based MIUI operating system which can be found on Xiaomi phones.
The tool was created because MIUI Notes does not allow for exporting notes in a standard way.

It has been tested with version `1.7.7` of the `com.miui.notes` package.

## Installing dependencies

Make a new virtual environement.

```console
py -2.7 -m virtualenv venv
venv\Scripts\activate
```

Manually install setuptools older than `45.0.0`.
Versions `45.0.0` and newer error out on versions of Python older than 3.5.
We need Python 2.7 because that's the only one that stable `androidviewclient` supports.

```console
pip install setuptools==44.1.1
```

Now install other dependencies

```console
pip install -r requirements.txt
```

## Usage

Make sure your device is visible in adb.

```console
adb devices
```

Make a directory named `exported_notes` and run the note extracting script.

```console
mkdir exported_notes
python -m script
```

This will create a pickle file with the extracted notes named similarly to `notes.2020-01-14_133258.pickle`.

To convert the pickle file into actual text files run the following script:

```console
python -m view_notes exported_notes/notes.2020-01-14_133258.pickle
```

This will create text files named `note_0.txt`, `note_1.txt` and so on in the current directory.
