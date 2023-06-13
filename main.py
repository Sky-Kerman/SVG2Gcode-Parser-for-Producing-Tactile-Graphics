'''
This is a project that converts an SVG file to a Gcode for you 3D printer. This project is part of the hardware team
workflow from the UW Tactile Graphics DRG Spring 2023.

This project utilizes svgpathtools library to get the paths and attribution to each path in a svg file. It then use the
"point" function within this library to convert it into points. Then, it goes through a gcode parser to generate gcode
for a 3D printer. The gcode parcer will handle the start and end gcode (currently tuned for ender 3 pro) and take x, y,
and z coordinates to generate the gcode in the middle.

This project is very preliminary currently (06/01/2023) and may or may not be updated in the future.
 
Author: Zichu (Sky) Song
Date: 06/01/2023
'''

import svgpathtools
from svgpathtools import svg2paths
import re
import math

#################################################### User Variables ####################################################

# File paths and names
inputFilePath = 'test.svg'
outputFileName = 'test'

# Printing specific parameters
layerHeight = 0.2 # height of each layer
totalHeight = 1.4 # the height of the heightest point in the entire svg file (how tactile you want the graph to be)
liftUpDistance = 1 # the distance the nozzle is lifted up when a segment is finished (retraction in z axis)
retraction = 5 # the distance the filament is retracted (retraction in E axis)

# Printer size (220x220 for ender 3 pro). Recommend to be the same as indicated by the slicing software.
printerX = 220 # width of the printer
printerY = 220 # depth of a printer



############################################## Not for User Manipulation ###############################################
searchPos = 0 # (LEGACY Function) the position of the start of a search
gcode = open(outputFileName+'.gcode', "w") # start writing to the gcode file
extruionMultiplier = 0.033 * 3 # extrusion multiplier. will change the amount of material extruded if changed
extrusion = -retraction * extruionMultiplier # keep track of how much material is extruded.
                                             # need to be negative to cancel the first "retraction cancelling" function



################################################# Predefined Functions #################################################

def start_gcode(printT=215, bedT=0):
    # starting sequence
    gcode.write("; Ender 3 Custom Start G-code\n")
    gcode.write("G92 E0 ; Reset Extruder\n")
    gcode.write("G28 ; Home all axes\n")

    gcode.write(f"M140 S{bedT} ;set bed temperature\n")
    gcode.write("M105\n")
    gcode.write(f"M190 S{bedT} ;wait for bed temperature\n")
    gcode.write(f"M104 S{printT} ;set hotend temperature\n")
    gcode.write("M105\n")
    gcode.write(f"M109 S{printT} ;wait for hotend temperature\n")
    gcode.write("M82 ;absolute extrusion mode\n")

    gcode.write("G1 Z2.0 F3000 ; Move Z Axis up little to prevent scratching of Heat Bed\n")
    gcode.write("G1 X0.1 Y20 Z0.3 F5000.0 ; Move to start position\n")
    gcode.write("G1 X0.1 Y200.0 Z0.3 F1500.0 E15 ; Draw the first line")
    gcode.write("G1 X0.4 Y200.0 Z0.3 F5000.0 ; Move to side a little\n")
    gcode.write("G1 X0.4 Y20 Z0.3 F1500.0 E30 ; Draw the second line")
    gcode.write("G92 E0 ; Reset Extruder\n")
    gcode.write("G1 Z2.0 F3000 ; Move Z Axis up little to prevent scratching of Heat Bed\n")
    gcode.write("G1 X5 Y20 Z0.3 F5000.0 ; Move over to prevent blob squish\n")
    gcode.write("G92 E0\n")
    gcode.write("G1 F2700 E-5 ;retract a little to prevent stringing\n")
    gcode.write("\n")

def end_gcode():
    # ending sequence
    gcode.write("\n")
    gcode.write("M140 S0\n")
    gcode.write("G91 ;Relative positioning\n")
    gcode.write("G1 E-2 F2700 ;Retract a bit\n")
    gcode.write("G1 E-2 Z0.2 F2400 ;Retract and raise Z\n")
    gcode.write("G1 X5 Y5 F3000 ;Wipe out\n")
    gcode.write("G1 Z10 ;Raise Z more\n")
    gcode.write("G90 ;Absolute positioning\n")
    gcode.write("M84 X Y E ;Disable all steppers but Z\n")
    gcode.write("M104 S0\n")
    gcode.write(";End of Gcode")

    gcode.close()
    print('gcode writing finished')

def write_1_seg(x, y, z, feedRate=1200, offset=0):
    global extrusion
    # create 1 printing segment
    gcode.write(f"G0 X{x[0]} Y{y[0]} Z{z[0]};move the nozzle to the first position\n")
    extrusion = extrusion + retraction # cancel the retraction
    gcode.write(f"G1 F{feedRate} E{extrusion} ;set up feedrate and move the filament right at the nozzle\n")

    for i in range(1, len(x)):
        # calculate distance between the previous point and this point to get extrusion rate
        length = math.sqrt((x[i] - x[i - 1]) ** 2 + (y[i] - y[ i - 1]) ** 2)
        extrusion = extrusion + length * extruionMultiplier
        gcode.write(f"G1 X{x[i] + offset} Y{y[i] + offset} Z{z[i]} E{extrusion};\n")

    # retraction
    extrusion = extrusion - retraction
    gcode.write(f"G1 F3500 E{extrusion} ;retration\n")
    gcode.write(f"G0 Z{z[-1] + liftUpDistance} ;increase z when moving over\n")

def determineHeight(attributes):
    try:
        strokeColor = attributes[i]['stroke']
        strokeColor = strokeColor.lstrip('#')
    except:
        print("Warning: stroke color not found. Set to black")
        strokeColor = 'Black'

    if strokeColor[0:3] == 'url':
        raise Exception('Do NOT use gradient')

    if strokeColor == 'Black' or strokeColor == 'black':
        grayscale = 0
    else:
        RGB = tuple(int(strokeColor[i:i + 2], 16) for i in (0, 2, 4))
        grayscale = sum(RGB) / len(RGB)

    # if not strokeColor == None and strokeColor[0:3] == 'url':
    #     searchStart = strokeColor.find('(') + 2
    #     searchEnd = strokeColor.find(')')
    #     search = strokeColor[searchStart:searchEnd]
    #     pos = fileString.find(search, searchPos) + len(search)
    #     print(fileString)
    #     print(searchPos)
    #     print(pos)
    #     print(search)
    #     print(strokeColor)

    strokeHeight = (255 - grayscale) / 255 * totalHeight
    return strokeHeight

def determineWidth(attributes):
    try:
        strokeWidth = attributes[i]['stroke-width']
    except:
        print("Warning: stroke width not found. Setting to 1 automatically")
        strokeWidth = 1

    return strokeWidth





################################################ Actual Functional Code ################################################

start_gcode()

# with open(inputFilePath, "r") as svgFile:
#     fileString = svgFile.read()
#     searchPos = fileString.find('Gradient')

path, attributes = svg2paths(inputFilePath)
layerCount = []
for i in range(len(path)):
    height = determineHeight(attributes)
    layerCount.append(round(height / layerHeight))
    strokeWidth = determineWidth(attributes)

    if layerCount[i] > 0:
        j = 0
        while j < len(path[i]):
            thisPath = path[i][j]
            # print(thisPath)
            x_local = []
            y_local = []
            z_local = []
            if isinstance(thisPath, svgpathtools.path.Line):
                for k in range(len(thisPath)):
                    point = thisPath[k]
                    x_local.append(point.real)
                    y_local.append(printerY - point.imag)
                    z_local.append(layerHeight)
            else:
                try:
                    for param in range(0, 11, 1):
                        param = param / 10
                        point = thisPath.point(param)
                        x_local.append(point.real)
                        y_local.append(printerY - point.imag)
                        z_local.append(layerHeight)
                except:
                    pass

            try:
                nextPath = path[i][j+1]
            except:
                nextPath = None

            while not nextPath == None and thisPath.end == nextPath.start:
                thisPath = nextPath
                j = j + 1
                if isinstance(thisPath, svgpathtools.path.Line):
                    for k in range(len(thisPath)):
                        point = thisPath[k]
                        x_local.append(point.real)
                        y_local.append(printerY - point.imag)
                        z_local.append(layerHeight)
                else:
                    try:
                        for param in range(0, 11, 1):
                            param = param / 10
                            point = thisPath.point(param)
                            x_local.append(point.real)
                            y_local.append(printerY - point.imag)
                            z_local.append(layerHeight)
                    except:
                        pass
                try:
                    nextPath = path[i][j+1]
                except:
                    nextPath = None
            j = j + 1
        write_1_seg(x_local, y_local, z_local)


layerCount =  [x - 1 for x in layerCount]
currentLayer = 2
while max(layerCount) > 0:
    for i in range(len(path)):
        if layerCount[i] > 0:
            j = 0
            while j < len(path[i]):
                thisPath = path[i][j]
                x_local = []
                y_local = []
                z_local = []
                if isinstance(thisPath, svgpathtools.path.Line):
                    for k in range(len(thisPath)):
                        point = thisPath[k]
                        x_local.append(point.real)
                        y_local.append(printerY - point.imag)
                        z_local.append(layerHeight*currentLayer)
                else:
                    try:
                        for param in range(0, 101, 1):
                            param = param / 100
                            point = thisPath.point(param)
                            x_local.append(point.real)
                            y_local.append(printerY - point.imag)
                            z_local.append(layerHeight*currentLayer)
                    except:
                        pass

                try:
                    nextPath = path[i][j + 1]
                except:
                    nextPath = None

                while not nextPath == None and thisPath.end == nextPath.start:
                    thisPath = nextPath
                    j = j + 1
                    if isinstance(thisPath, svgpathtools.path.Line):
                        for k in range(len(thisPath)):
                            point = thisPath[k]
                            x_local.append(point.real)
                            y_local.append(printerY - point.imag)
                            z_local.append(layerHeight*currentLayer)
                    else:
                        try:
                            for param in range(0, 101, 1):
                                param = param / 100
                                point = thisPath.point(param)
                                x_local.append(point.real)
                                y_local.append(printerY - point.imag)
                                z_local.append(layerHeight*currentLayer)
                        except:
                            pass
                    try:
                        nextPath = path[i][j + 1]
                    except:
                        nextPath = None

                j = j+1

            write_1_seg(x_local, y_local, z_local)

    layerCount = [x - 1 for x in layerCount]
    currentLayer = currentLayer + 1

end_gcode()
