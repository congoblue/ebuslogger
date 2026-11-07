import pifacecad
cad = pifacecad.PiFaceCAD()    # create PiFace Control and Display object
cad.lcd.backlight_on()         # turns the backlight on
cad.lcd.write("Hello, world!") # writes hello world on to the LCD

