
import sys
import shutil
import os
import re

from pathlib import Path

ref_dir = "/Users/wgroeneveld/development/java/gradlefxmlsample/"

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
			found = re.findall(r"class\s(.+)\sextends", code)
			return found[0]
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
		
		def move_image_to_resource_dir(image_argument):
			print("\t\tnew Image(\"" + image_argument + "\")")
			dest = self.src + "src/main/resources" + image_argument
			os.makedirs(os.path.dirname(dest), exist_ok=True)
			shutil.move(self.src + "src/main/java" + image_argument, dest)

		for path in Path(self.src + "src/main/java").rglob('*.java'):
			with open(path, "r") as file:
				code = file.read()
				if "new Image(" in code:
					for match in re.findall(r"new Image\(\"(.+)\"", code):
						move_image_to_resource_dir(match)


	def convert(self):
		self.assert_dir_exists()

		self.copy_grade_files()
		self.set_main_class_file()
		self.set_project_name()
		self.move_source_dir()
		self.move_resource_files()
		self.fix_class_resource_loading()
		self.fix_fximage_loads()

		print("Done! check out " + self.src)


if __name__ == "__main__":
	if len(sys.argv) <= 1:
		print("Forgot argument?")
	else:
		Converter(sys.argv[1]).convert()
