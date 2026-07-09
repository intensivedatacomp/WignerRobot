def handle_key_press(event, root, Control, settings):
    
    # Control keys
    if event.keysym == 'b':
        Control.pressed_l = False
        if Control.pressed_b:
            Control.buzzer = "empty"
            Control.pressed_b = False
        else:
            Control.pressed_b = True
        return
    if event.keysym.lower() == 'l':
        Control.pressed_b = False
        if Control.pressed_l:
            Control.pressed_l = False
        else:
            Control.pressed_l = True
        return

    # Song control
    if event.keysym.lower() == 'v' and Control.pressed_b:
        Control.buzzer = "violent"
        Control.pressed_b = False
        return
    if event.keysym.lower() == 'n' and Control.pressed_b:
        Control.buzzer = "nino"
        Control.pressed_b = False
        return
    if  event.keysym.lower() == 'y' and Control.pressed_b:
        Control.buzzer = "supermario"
        Control.pressed_b = False
        return
    if event.keysym.lower() == 'm' and Control.pressed_b:
        Control.buzzer = "masiksong"
        Control.pressed_b = False
        return

    Control.pressed_l = False
    Control.pressed_b = False
       
    if event.keysym == 'Escape' or event.keysym.lower() == 'q':
        Control.shutdown = True
        return

    # Movement control
    if event.keysym == 'Down':
        accelerateCar(Control, -1, settings)
        return
    if event.keysym == 'Up':
        accelerateCar(Control, 1, settings)
        return
    if event.keysym == 'Right':
        turnCar(Control, 1, settings)
        return
    if event.keysym == 'Left':
        turnCar(Control, -1, settings)
        return
    if event.keysym == 'space':
        Control.speed = [0,0]
        Control.angles = settings["DEFAULT_ANGLES"][:]
        return
    
    # Servo control
    if event.keysym.lower() == "a": 
        turnServo(Control, 1, 1, settings)
        return
    if event.keysym.lower() == "d":
        turnServo(Control, 1, -1, settings)
        return
    if event.keysym.lower() == "s":
        turnServo(Control, 2, 1, settings)
        return
    if event.keysym.lower() == "w":
        turnServo(Control, 2, -1, settings)
        return
    if event.keysym.lower() == "o":
        turnServo(Control, 0, 1, settings)
        return
    if event.keysym.lower() == "p":
        turnServo(Control, 0, -1, settings)
        return

    # US sensor control
    if event.keysym.lower() == 'm':
        Control.us_measuring = not Control.us_measuring



def accelerateCar(Control, sgn, settings):
        if sgn == 0:
            Control.speed = [0,0]
            return
        elif sgn > 0:
            Control.speed[0] = min(Control.speed[0] + settings["ACCELERATION"], settings["MAX_SPEED"])
            Control.speed[1] = min(Control.speed[1] + settings["ACCELERATION"], settings["MAX_SPEED"])
        elif sgn < 0:
            Control.speed[0] = max(Control.speed[0] - settings["ACCELERATION"], settings["MIN_SPEED"])
            Control.speed[1] = max(Control.speed[1] - settings["ACCELERATION"], settings["MIN_SPEED"])

def turnCar(Control, sgn, settings):
    if sgn == -1:
        Control.speed[0] = max(Control.speed[0] - settings["ACCELERATION"], settings["MIN_SPEED"])
        Control.speed[1] = min(Control.speed[1] + settings["ACCELERATION"], settings["MAX_SPEED"])
    elif sgn == 1:
        Control.speed[0] = min(Control.speed[0] + settings["ACCELERATION"], settings["MAX_SPEED"])
        Control.speed[1] = max(Control.speed[1] - settings["ACCELERATION"], settings["MIN_SPEED"])

def turnServo(Control, index, sgn, settings):
    if sgn == 1:
        Control.angles[index] = min(Control.angles[index] + settings["ANGLE_STEP"], 180)
    elif sgn == -1:
        Control.angles[index] = max(Control.angles[index] - settings["ANGLE_STEP"], 0)