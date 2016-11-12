import os
import json
import time
import select
import socket
import base64
from threading import Thread
from PIL import Image

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GObject

you = {"name": "", "pass": "Lobby", "jpeg": ""}
jpgnum = 0

css = b"""
#bordered {
	border-bottom: 1px dotted white;
	font: Cantarell;
}

#blued {
	font-size: 8pt;
	font-weight: bold;
	color: #2cf;
}

#clocked {
	font-size: 6pt;
	color: #aaa;
}

#txted {
	font-size: 8pt;
	padding-right: 50px;
}
"""

def save():
	temp = os.getenv("TEMP")
	f = open(temp + "/amchat2.json", "w")
	f.write(json.dumps(you))
	f.close()

class AMGrid(Gtk.Grid):
	def __init__(self, name, text, admin, jpeg):
		Gtk.Grid.__init__(self)
		
		pre = "<"
		post = ">"
		if admin == True:
			pre = "{ "
			post = " }"
		
		global jpgnum
		jpgnum = (jpgnum + 1 ) % 20
		outf = os.getenv("TEMP") + "/amchat_jpeg" + str(jpgnum) + ".jpeg"
		fp = open(outf, "wb")
		fp.write(base64.b64decode(jpeg.encode()))
		fp.close()
		img = Gtk.Image.new_from_file(outf)
		img.set_size_request(100, 50)
		self.attach(img, 0, 0, 1, 3)
		
		lab = Gtk.Label(time.strftime("%H:%M:%S", time.localtime()))
		lab.set_alignment(xalign=0.9, yalign=1.0)
		lab.set_size_request(500, 20)
		lab.set_name("clocked")
		self.attach(lab, 1, 0, 1, 1)
		
		lbl = Gtk.Label(pre + name + post)
		lbl.set_alignment(xalign=0.0, yalign=0.5)
		lbl.set_size_request(500, 20)
		lbl.set_name("blued")
		self.attach(lbl, 1, 1, 1, 1)
		
		tevi = Gtk.TextView()
		buf = tevi.get_buffer()
		buf.set_text(text + "\n")
		tevi.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
		tevi.set_editable(False)
		tevi.set_cursor_visible(False)
		tevi.set_size_request(500, 10)
		tevi.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.0, 0.0, 0.0, 0.0))
		tevi.set_name("txted")
		tevi.set_justification(Gtk.Justification.FILL)
		self.attach(tevi, 1, 2, 1, 1)
		
		self.set_name("bordered")
		self.show_all()

class AMWindow(Gtk.Window):
	def __init__(self):
		Gtk.Window.__init__(self, title="AM-Chat")
		self.set_size_request(600, 400)
		self.set_resizable(False)
		
		self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.nected = False
		self.flashing = False
		
		grid = Gtk.Grid()
		self.add(grid)
		
		scrolla = Gtk.ScrolledWindow()
		scrolla.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
		self.vboxa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		out = "Hallo " + you["name"] + " @ " + you["pass"] + "!\nUm einen Befehl zu starten, fange deine Eingabe mit einem Punkt an.\n.n um Deinen Namen zu setzen zB: .n John\n.r um Deinen Raum zu setzen zB: .r wc\n.a um Deinen Avatar zu setzen\nSind alle Angaben gemacht, kannst Du mit .c eine Verbindung aufbauen und mit .d die Verbindung trennen."
		self.vboxa.pack_start(AMGrid("AM-Chat", out, True, you["jpeg"]), False, False, 0)
		scrolla.add_with_viewport(self.vboxa)
		scrolla.set_size_request(600, 370)
		self.vert = scrolla.get_vadjustment()
		self.isbottom = True
		self.vboxa.connect("size-allocate", self.auto_scroll)
		self.vert.connect("value-changed", self.check_bottom)
		
		grid.attach(scrolla, 0, 0, 2, 2)
		
		self.entry = Gtk.Entry()
		self.entry.set_text("")
		self.entry.set_editable(True)
		self.entry.connect("activate", self.activated)
		self.entry.set_size_request(600, 30)
		
		grid.attach(self.entry, 0, 2, 2, 1)
		self.entry.grab_focus()
		self.connect("focus-in-event", self.unflash)

	def unflash(self, widget, event):
		if self.flashing == True:
			self.set_urgency_hint(False)
			self.flashing = False
	
	def check_bottom(self, widget):
		if self.vert.get_value() + 1.0 >= self.vert.get_upper() - self.vert.get_page_size():
			self.isbottom = True
		else:
			self.isbottom = False

	def auto_scroll(self, widget, event):
		if self.isbottom == True:
			self.vert.set_value(self.vert.get_upper() - self.vert.get_page_size())

	def new_msg(self, name, text, admin, jpeg):
		self.vboxa.pack_start(AMGrid(name, text, admin, jpeg), False, False, 0)
		if self.is_active() == False:
			self.set_urgency_hint(True)
			self.flashing = True
	
	def activated(self, widget):
		intxt = self.entry.get_text()
		if intxt[:1] == ".":
			if intxt[1:2] == "n" and self.nected == False:
				you["name"] = intxt[3:]
				out = "Dein Name ist nun gespeichert als: " + you["name"]
				self.new_msg("AM-Chat", out, True, you["jpeg"])
				save()
			elif intxt[1:2] == "r" and self.nected == False:
				you["pass"] = intxt[3:]
				out = "Dein Raum ist nun gespeichert als: " + you["pass"]
				self.new_msg("AM-Chat", out, True, you["jpeg"])
				save()
			elif intxt[1:2] == "c":
				out = "Versuche Verbindung aufzubauen..."
				self.new_msg("AM-Chat", out, True, you["jpeg"])
				if self.cnect() == False:
					out = "Verbindung gescheitert!"
					self.new_msg("AM-Chat", out, True, you["jpeg"])
				else:
					self.new_msg("AM-Chat", "Verbindung steht!", True, you["jpeg"])
					self.nected = True
			elif intxt[1:2] == "d" and self.nected == True:
				self.nected = False
				self.conn.close()
				self.new_msg("AM-Chat", "Verbindung getrennt!", True, you["jpeg"])
			elif intxt[1:2] == "a" and self.nected == False:
				dialog = Gtk.FileChooserDialog("Wähle ein Bild", self, Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
				filter = Gtk.FileFilter()
				filter.set_name("Bilder")
				filter.add_mime_type("image/jpeg")
				dialog.add_filter(filter)
				rc = dialog.run()
				if rc == Gtk.ResponseType.OK:
					try:
						im = Image.open(dialog.get_filename())
						im.thumbnail((64,64))
						outf = os.getenv("TEMP") + "/amchat_self.jpeg"
						im.save(outf, "JPEG")
						fp = open(outf, "rb")
						you["jpeg"] = base64.b64encode(fp.read()).decode("utf-8")
						fp.close()
						self.new_msg("AM-Chat", "Avatar geändert!", True, you["jpeg"])
						save()
					except:
						self.new_msg("AM-Chat", "Avatar konnte nicht geändert werden!", True, you["jpeg"])
				dialog.destroy()
		else:
			out = "msg " + base64.b64encode(intxt.encode()).decode("utf-8") + "\n"
			try:
				self.conn.send(out.encode())
			except:
				self.new_msg("AM-Chat", "Nachricht konnte nicht gesendet werden!", True, you["jpeg"])
		self.entry.set_text("")

	def cnect(self):
		try:
			self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.conn.connect(("188.68.38.124", 20502))
		except:
			return False
		
		name = base64.b64encode(you["name"].encode()).decode("utf-8")
		room = base64.b64encode(you["pass"].encode()).decode("utf-8")
		jpeg = base64.b64encode(you["jpeg"].encode()).decode("utf-8")
		out = "login " + name + " " + room + " " + jpeg + "\n"
		try:
			self.conn.send(out.encode())
		except:
			return False
		return True
		
temp = os.getenv("TEMP")
try:
	f = open(temp + "/amchat2.json", "r")
	you = json.loads(f.read())
	f.close()
except:
	you["name"] = os.getenv("USER")
	fp = open("avatar.jpeg", "rb")
	you["jpeg"] = base64.b64encode(fp.read()).decode("utf-8")
	fp.close()

sp = Gtk.CssProvider()
sp.load_from_data(css)
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), sp, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

isrunnin = True
win = AMWindow()

def infiloop():
	while isrunnin:
		inbuf = b""
		LRT = time.time()
		while win.nected:
			rd, wd, xd = select.select([win.conn], [], [], 0.05)
			
			if not rd:
				if time.time() > LRT + 20.0:
					LRT = time.time()
					out = "ping\n"
					try:
						win.conn.send(out.encode())
					except:
						win.conn.close()
						win.nected = False
						break
				continue
			
			else:
				dta = None
				try:
					dta = win.conn.recv(1)
				except:
					pass
				if not dta:
					win.conn.close()
					win.nected = False
					GObject.idle_add(win.new_msg, "AM-Chat", "Verbindung verloren!", True, you["jpeg"])
					break
				
				if dta == b"\n":
					try:
						txt = inbuf.decode("utf-8").split(" ")
					except:
						win.conn.close()
						win.nected = False
						GObject.idle_add(win.new_msg, "AM-Chat", "Verbindung verloren!", True, you["jpeg"])
						break
					inbuf = b""
					
					if len(txt) == 2 and txt[0] == "error":
						intxt = base64.b64decode(txt[1].encode()).decode("utf-8")
						GObject.idle_add(win.new_msg, "Server", intxt, True, you["jpeg"])
					
					if len(txt) == 4 and txt[0] == "msg":
						name = base64.b64decode(txt[1].encode()).decode("utf-8")
						intxt = base64.b64decode(txt[2].encode()).decode("utf-8")
						jpeg = base64.b64decode(txt[3].encode()).decode("utf-8")
						GObject.idle_add(win.new_msg, name, intxt, False, jpeg)

				else:
					inbuf += dta
		time.sleep(0.2)

Thread(target=infiloop).start()

win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()

if win.nected == True:
	win.nected = False
	win.conn.close()
isrunnin = False
