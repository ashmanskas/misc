#! /usr/bin/env python3

#
# roster-anki-flash-cards.py
#
# convert saved web page (Firefox or Chrome format) from
# https://hosted.apps.upenn.edu/PennantReports/ClassListInstructor.aspx
# into an Anki flashcard deck, for learning student names
#
# begun 2025-11-21 : Bill Ashmanskas : ashmansk@hep.upenn.edu
#
# 
# Note: By federal law, class lists are private. Do NOT share class
# lists or pictures publicly without every student's written
# permission.
#
# The intended use of this program is for the private use of
# individual instructors to learn their own students' names at the
# start of a new semester.  Harvey Mudd College, for example, makes
# analogous Anki flashcard decks centrally available to instructors:
# 
#     - https://www.hmc.edu/cis/services/anki-flash-cards/
#
# I have been using flashcards to learn my own students' names for
# several years now, a couple of weeks before each new semester
# begins.  I recently rewrote my code to make it easier for other
# (somewhat computer-savvy) Penn instructors to use Anki flashcards
# to memorize their own students' names.
#
# Related project, which I found after writing this:
#
#   - https://github.com/jlumbroso/anki-deck-generator
#
# Anki, by the way, is a convenient way to memorize almost anything.
# I majored in physics in part because of a dislike for memorization.
# If Anki had been around in 1989, I might have enjoyed organic
# chemistry!
#
#
# Usage:
#
#  - Ensure that you have a working python3.  Use pip to install two
#    external packages: 'beautifulsoup4' and 'genanki'.
#
#  - Use either Firefox or Chrome to get your "Instructor Class List"
#    from Pennant via https://courses.at.upenn.edu/instructor/landing
#
#  - Be sure to include photos, which I think only works if your
#    search returns just a single section's students.
#
#  - Use the browswer's "save page as" feature (format: web page,
#    complete) to save the page content, typically to your downloads
#    folder to a file called 'Instructor Class List.html' and a data
#    folder called ''Instructor Class List_files'.  You will want to
#    run this python program from this downloads folder.
#
#  - Run the program:  python3 roster-anki-flash-cards.py
#
#  - By default, it will produce 'anki.apkg' as output.  If you have
#    the Anki software installed, double-clicking this file will
#    prompt you to import the flashcard deck into Anki.  The Anki
#    software is available at
#
#        - https://apps.ankiweb.net/
#

import argparse
import re
import shutil
import sys

import urllib.parse

from pprint import pprint
from types import SimpleNamespace

# python3 -m pip install beautifulsoup4
from bs4 import BeautifulSoup

# python3 -m pip install genanki
import genanki


# https://github.com/kerrickstaley/genanki/#note-guids
class MyNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0], self.fields[1])


class Roster:

    def argparse(self):
        # Use 'argparse' module to parse command-line arguments:
        # follows Beazley cookbook recipe 13.3
        parser = argparse.ArgumentParser(
            description="convert Pennant roster into Anki flash cards")
        parser.add_argument(
            "--input", nargs="?", default="",
            help="html file to read, eg 'Instructor Class List.html'")
        parser.add_argument(
            "--output", nargs="?", default="",
            help="filename for anki deck archive")
        parser.add_argument("--verbose", action="store_true")
        self.parser = parser
        self.args = parser.parse_args()
        self.verbose = self.args.verbose
        self.ifnam = self.args.input
        if not self.ifnam:
            self.ifnam = "Instructor Class List.html"
        self.ofnam = self.args.output
        if not self.ofnam:
            self.ofnam = "anki.apkg"
        if self.verbose:
            print(f"args = {self.args}")
            print(f" ifnam = {self.ifnam}")
            print(f" ofnam = {self.ofnam}")

    def read_roster(self):
        # Build up list of student records
        self.roster = []  
        # BeautifulSoup recipe from duck.ai assist
        with open(self.ifnam, "r", encoding="utf-8") as fp:
            html_content = fp.read()
        soup = BeautifulSoup(html_content, "html.parser")
        self.soup = soup
        title = soup.title.string.strip()
        assert (title == "Instructor Class List")
        # name eg 'PHYS-0150-401-202610'
        course_email = [
            x for x in soup.find_all("a") if "@lists" in str(x.contents)][0]
        course_email = course_email.contents[0]
        self.course_name = course_email.split("@")[0]
        # table contains list of students
        t = soup.find("table", class_="ClassListTable")
        rows = t.find_all("tr", class_="pdfClassListEntry")
        for r in rows:
            # record to hold this student's data
            o = SimpleNamespace()
            o.photo = r.find("img").attrs["src"]
            o.photo = urllib.parse.unquote(o.photo)
            info = r.find_all("td")[1]  # second datum is student info
            # pick out desired contents of datum
            info = [x for x in info if x.name!="br"]
            tags = info[0::2]
            data = info[1::2]
            for i,t in enumerate(tags):
                # get 'Tag:' from '<b>Tag: </b>'
                t = t.contents[0].strip()
                # downcase and remove colon
                t = t.lower().replace(":", "").replace(" ", "")
                # corresponding datum for this tag
                d = data[i]
                # each tag becomes an attribute of student record
                o.__dict__[t] = d
            o.advisor = " ".join(o.advisor.split(",")[::-1])
            o.email = o.emailaddress.contents[0]
            o.lname = o.name.split(",")[0]
            o.fname = o.name.split(",")[1]
            o.name = " ".join(o.name.split(",")[::-1])
            o.major = o.primarymajor.split()[0]
            o.year = o.classification
            pprint(o.__dict__)
            self.roster.append(o)

    def rename_photos(self):
        # use student name for photo instead of opaque filename
        for r in self.roster:
            oldfnam = r.photo
            newfnam = f"photo-{r.lname.lower()}-{r.fname.lower()}.jpg"
            newfnam = newfnam.replace(" ", "-")
            # copy, don't rename, so that I can rerun program
            shutil.copy(oldfnam, newfnam)
            r.photo_renamed = newfnam
            
    def make_flashcards(self):
        model_id = hash(str(self.course_name)) & 0x7fffffff
        # https://github.com/kerrickstaley/genanki
        model = genanki.Model(
            model_id,
            "My Model",
            fields=[
                {"name": "Prompt"},
                {"name": "Photo"},
                {"name": "Answer"},
                ],
            templates=[
                {
                    "name": "Card 1",
                    "qfmt": "{{Prompt}}<br>{{Photo}}",
                    "afmt": '{{FrontSide}}<hr id="answer">{{Answer}}'
                    },
                ],
            sort_field_index=2)
        deck_id = model_id
        deck_name = self.course_name
        deck = genanki.Deck(deck_id, deck_name)
        # generate a "note" (basically a flash card) for each student
        media_files = []
        for o in self.roster:
            answer = (
                f"{o.name}<br/>\n" +
                f"{o.year} / {o.major}<br>\n" +
                f"{o.email}<br>\n" +
                f"advisor: {o.advisor}<br>\n")
            prompt = f"{self.course_name}<br/>"
            note = MyNote(
                model=model,
                fields=[prompt,
                        f'<img src="{o.photo_renamed}">',
                        answer])
            deck.add_note(note)
            media_files.append(f"{o.photo_renamed}")
        package = genanki.Package(deck)
        package.media_files = media_files
        package.write_to_file(self.ofnam)
        print(f"wrote anki flashcards to {self.ofnam}")
        #import pdb; pdb.set_trace()

                
    def main(self):
        # This 'Roster' class is essentially a main program, organized
        # into a class, so that there is an obvious, non-global place
        # to store program state information.
        self.argparse()
        self.read_roster()
        self.rename_photos()
        self.make_flashcards()


# If invoked as main program (vs import from elsewhere), then
# instantiate 'Roster' and run it.
if __name__ == "__main__":
    o = Roster()
    o.main()
