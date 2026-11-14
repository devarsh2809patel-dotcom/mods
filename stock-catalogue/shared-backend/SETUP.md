# Shared stock catalogue: one-time setup (about 15 minutes)

The shared database is a Google Sheet in **your** Google account. Everyone who opens the Stock Catalogue Studio with the team passcode reads and edits that same sheet. Nobody needs a Claude or Google login.

## 1. Create the sheet and paste the script

1. Open https://sheets.google.com and create a **blank** spreadsheet. Name it `Stock Catalogue Database`.
2. In the menu, click **Extensions → Apps Script**. A code editor opens.
3. Delete everything in the editor. Paste the full contents of `Code.gs` (in this folder).
4. Find the line `const PASSCODE = 'CHANGE-ME';` and replace `CHANGE-ME` with your own team passcode.
   * Use at least 10 characters, for example `Loha2026Navapura`.
   * Keep the quote marks.
5. Click the **Save** icon (the floppy disk).

## 2. Publish it as a web app

1. Click **Deploy → New deployment**.
2. Click the gear next to "Select type" and choose **Web app**.
3. Fill in:
   * Description: `Stock catalogue`
   * Execute as: **Me**
   * Who has access: **Anyone**
4. Click **Deploy**, then **Authorize access** and choose your Google account.
5. Google shows "Google hasn't verified this app". This is normal for your own script. Click **Advanced → Go to … (unsafe) → Allow**.
6. Copy the **Web app URL**. It ends in `/exec`. This is your *shared catalogue address*.

"Anyone" only means the address can be reached. Without the passcode it returns nothing.

## 3. Connect the Studio and load the stock once

1. Open `Stock_Catalogue_Studio.html`.
2. Paste the shared catalogue address, type the passcode and your name, then press **Connect**.
3. Press **Load starting stock**. This happens only once; it fills the sheet with both firms' articles.

## 4. Give it to the family

Send them:
* the Studio file (or the web link, if you host it)
* the shared catalogue address
* the passcode

Each person connects once per phone or computer. After that, the Studio opens straight to the shared list.

To make it simpler for them, ask Claude (or run the command below) to build the address into the file. They then only type the passcode:

```
python artifact/build_standalone.py --api-url https://script.google.com/macros/s/XXXX/exec
```

## How it behaves

* Every change saves to the sheet within a second. The status at the top says **Saved for everyone**.
* Other people's changes appear within about 30 seconds. On the Versions tab, **Check for changes now** fetches them immediately.
* If two people change the same category at the same moment, the second person sees a warning and the other person's version. Nothing is overwritten silently. They redo their last change.
* Exported versions are stored in the sheet too, so anyone can download any version.
* **Backups:** in Google Sheets, use **File → Version history**. In the Studio, use **Versions → Download data file**.
* Do not type into the `data` sheet by hand. Its cells hold the catalogue in a coded form; edit through the Studio only.

## Changing things later

* **New passcode:** edit the `PASSCODE` line, then go to **Deploy → Manage deployments → ✏️ Edit → Version: New version → Deploy**. The address stays the same, and everyone reconnects once with the new passcode.
* **Updated `Code.gs` from Claude:** paste it in, then publish a new version the same way.
* **Removing someone's access:** change the passcode.
