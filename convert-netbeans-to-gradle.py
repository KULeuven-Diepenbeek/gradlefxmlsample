
import sys
import shutil
import os
import re
import csv

from pathlib import Path

ref_dir = "/Users/wgroeneveld/development/java/gradlefxmlsample/"

# https://stackoverflow.com/questions/2319019/using-regex-to-remove-comments-from-source-files
def remove_comments(string):
    pattern = r"(\".*?(?<!\\)\"|\'.*?(?<!\\)\')|(/\*.*?\*/|//[^\r\n]*$)"
    # first group captures quoted strings (double or single)
    # second group captures comments (//single-line or /* multi-line */)
    regex = re.compile(pattern, re.MULTILINE|re.DOTALL)
    def _replacer(match):
        # if the 2nd group (capturing comments) is not None,
        # it means we have captured a non-quoted (real) comment string.
        if match.group(2) is not None:
            return "" # so we will return empty to remove the comment
        else: # otherwise, we will return the 1st group
            return match.group(1) # captured quoted-string
    return regex.sub(_replacer, string)


class Converter():
	def __init__(self, src):
		self.src = os.path.abspath(src) + "/"
		self.projectname = ""

	def assert_dir_exists(self):
		if not os.path.isdir(ref_dir) or not os.path.isdir(self.src) or not os.path.exists(self.src):
			print("input is not a valid directory!")
			exit()

	def copy_grade_files(self):
		print("\t1. Copying gradle reference files...")
		try:
			shutil.copytree(ref_dir + "gradle", self.src + "gradle")
		except OSError as exc:
			print("\t\tgradle folder already exists?")
		
		shutil.copy(ref_dir + "build.gradle", self.src + "build.gradle")
		shutil.copy(ref_dir + "gradlew", self.src + "gradlew")
		shutil.copy(ref_dir + "gradlew.bat", self.src + "gradlew.bat")


	def set_main_class_file(self):
		print("\t2. Retrieving and setting main class file...")

		def read_package(code):
			found = re.findall(r"package\s(.+);", code)
			return found[0]
		def read_class(code):
			for regex in [ r"class\s(.+)\sextends", r"public class\s(.+)\{", r"public class\s(.+)" ]:
				found = re.findall(regex, code)
				if len(found) > 0:
					return found[0].strip()
			raise Exception("No main class found")
		def replace_main_class_name(to_replace, replace_with):
			with open(self.src + "build.gradle", "r") as file:
				data = file.read()
			data = data.replace(to_replace, replace_with)
			with open(self.src + "build.gradle", "w") as file:
				file.write(data)

		for path in Path(self.src + "src").rglob('*.java'):
			with open(path, "r") as file:
				code = file.read()
				if "void main(" in code:
					break
		pkg = read_package(code)
		main_cls = read_class(code)
		print("\t\tFound main class: " + pkg + "." + main_cls)
		self.projectname = pkg

		replace_main_class_name("be.kuleuven.JavaFXMain", pkg + "." + main_cls)

	def set_project_name(self):
		print("\t3. Setting project dir name... to pkg " + self.projectname)
		settings_gradle_contents = "rootProject.name = '" + self.projectname + "'"
		with open(self.src + "settings.gradle", "w") as setting:
			setting.write(settings_gradle_contents)

	def move_source_dir(self):
		print("\t4. Moving stuff to src/main/java...")
		for srcdir in os.listdir(self.src + "src/"):
			try:
				shutil.move(self.src + "src/" + srcdir, self.src + "src/main/java/" + srcdir)
			except OSError as exc:
				print("\t\tAlready moved into src/main/java?")

	def move_resource_files(self):
		print("\t5. Moving resources to src/main/resources...")
		resources_dir = self.src + "src/main/resources/"

		if not os.path.exists(resources_dir):
			os.mkdir(resources_dir)
		
		for file in Path(self.src + "src/main/java").rglob('*.fxml'):
			print("\t\tMoving res. " + file.name)
			shutil.move(file.absolute().as_posix(), resources_dir)

	def fix_class_resource_loading(self):
		print("\t6. Fixing getClass().getResource()...")

		files = []
		for path in Path(self.src + "src/main/java").rglob('*.java'):
			with open(path, "r") as file:
				code = file.read()
				if "getClass().getResource(" in code:
					print("\t\t in " + path.name)
					files.append(path)

		for filepath in files:
			with open(filepath, "r") as file:
				data = file.read()
			data = data.replace("getClass().getResource(\"", "getClass().getClassLoader().getResource(\"")
			with open(filepath, "w") as file:
				file.write(data)

	def fix_fximage_loads(self):
		print("\t7. Fixing new Image(...) resource loads...")
		
		# possible formats:
		# 	/Image/bla.png
		#	file:dir\\subdir\\bla.png
		def move_image_to_resource_dir(image_argument):
			image_argument = image_argument.replace("file:src", "/").replace("\\\\", "/")

			print("\t\tnew Image(\"" + image_argument + "\")")
			dest = self.src + "src/main/resources" + image_argument
			os.makedirs(os.path.dirname(dest), exist_ok=True)

			try:
				shutil.move(self.src + "src/main/java" + image_argument, dest)
			except OSError as exc:
				print("\t\t-- whoops, move gone wrong, already moved?")

		for path in Path(self.src + "src/main/java").rglob('*.java'):
			with open(path, "r") as file:
				code = file.read()
				if "new Image(" in code:
					for match in re.findall(r"new Image\(\"(.+)\"", code):
						move_image_to_resource_dir(match)

	def strip_comments(self):
		print("\t8. Removing comments... ")
		for path in Path(self.src + "src/main/java").rglob('*.java'):
			with open(path, "r") as file:
				code = remove_comments(file.read())
			with open(path, "w") as writable:
				writable.write(code)


	def convert(self):
		self.assert_dir_exists()

		self.copy_grade_files()
		self.set_main_class_file()
		self.set_project_name()
		self.move_source_dir()
		self.move_resource_files()
		self.fix_class_resource_loading()
		self.fix_fximage_loads()
		self.strip_comments()

		print("Done! check out " + self.src)


class MassConverter():
	def __init__(self, convertdir):
		self.convertdir = convertdir

	def move_projects_to_root(self):
		print("\tMoving project contents to root...")
		for project in os.listdir(self.convertdir):
			# 1. locate build.xml
			# 2. take contents of build.xml dir and move to root
			# 3. remove any subdir that's not src or test
			rootdir = self.convertdir + "/" + project
			globbuild = list(Path(rootdir).rglob('build.xml'))
			if len(globbuild) > 0:
				builddir = os.path.dirname(globbuild[0])

				for dirfilename in os.listdir(builddir):
					try:
						shutil.move(os.path.join(builddir, dirfilename), rootdir)
					except OSError as exc:
						pass # already in root, don't care

		print("\tDeleting every dir that's not src...")
		for project in os.listdir(self.convertdir):
			rootdir = self.convertdir + "/" + project
			if os.path.isdir(rootdir):
				for projectdir in os.listdir(rootdir):
					todel = os.path.join(rootdir, projectdir)
					if os.path.isdir(todel) and "src" not in todel:
						print("\t\tRemoving " + todel)
						shutil.rmtree(todel)

	def anonymize_dirs(self):
		print("\tAnonymizing student project dirs...")

		def write_student_mapping(rows):
			with open("student_mapping.csv", "w") as csvfile:
				writer = csv.writer(csvfile)
				writer.writerow(['studnr', 'aonymous_id'])
				writer.writerows(rows)
			print("\tstudent_mapping.csv written.")

		def convert_studnr_to_i():
			rows = []
			i = 1
			for project in os.listdir(self.convertdir):
				rootdir = self.convertdir + "/" + project

				if os.path.isdir(rootdir):
					trystudnr = re.findall(r"Verplichte taak_o-(\d+)", project)
					if len(trystudnr) > 0:
						studnr = trystudnr[0]
						print("\t\t" + str(studnr) + " => " + str(i))
						rows.append([studnr, str(i)])

						shutil.move(rootdir, self.convertdir + "/" + str(i))
						if os.path.exists(self.convertdir + "/" + str(i) + "__MACOSX"):
							print("\t\t\tWarning, __MACOSX garbage")
							shutil.rmtree(self.convertdir + "/" + str(i) + "__MACOSX")

						i = i + 1
			return rows

		rows = convert_studnr_to_i()
		if len(rows) > 0:
			write_student_mapping(rows)
		self.move_projects_to_root()

	def convert_each_project(self):
		for project in os.listdir(self.convertdir):
			rootdir = self.convertdir + "/" + project
			if os.path.isdir(rootdir):
				print("-- Converting " + project)
				Converter(rootdir).convert()

	def convert(self):
		self.anonymize_dirs()
		self.convert_each_project()



# manual pre-processing:
# ---
# find . -name '*.zip' -exec sh -c 'unzip -d "${1%.*}" "$1"' _ {} \;
# rm -rf *.zip
# find . -name '*.rar' -exec sh -c 'unrar x "$1" "${1%.*}/"' _ {} \;
# rm -rf *.rar
# find . -name '*.7z' -exec sh -c '7z x "$1" "-o ${1%.*}/"' _ {} \;
# rm -rf *.7z
# sudo find . -name ".DS_Store" -exec rm -rf {} \;
# sudo find . -name ".git" -exec rm -rf {} \;
# sudo find . -name ".gitignore" -exec rm -rf {} \;
# chmod -R 777 .

if __name__ == "__main__":
	if len(sys.argv) <= 1:
		print("Forgot argument? arg0: dir")
		exit()
	elif len(sys.argv) == 2:
		MassConverter(sys.argv[1]).convert()
		print("--- DONE! ")
	else:
		Converter(sys.argv[1]).convert()
		print("--- DONE! ")
