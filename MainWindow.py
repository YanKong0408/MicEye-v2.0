import glob
import time
import cv2
from PyQt5 import QtGui
from PyQt5.QtCore import Qt,QPoint,QRect,QTimer
from PyQt5.QtGui import QKeyEvent, QFont,QPixmap,QPainter,QPen,QColor
from PyQt5.QtWidgets import (QWidget, QGroupBox, QPushButton, QFileDialog,QDesktopWidget,QFrame,
                             QLabel, QSizePolicy,QVBoxLayout, QHBoxLayout,QGridLayout,QScrollArea)
import random
import json
from utils.dataUtils import CsvLog
from utils.annoUtils import parseLabelmeXMl
from utils.gazeUtils import eyeTrackerInit,getGazeCenter, getGazeRaw
from utils.imageUtils import (createPixmapFromArray, imRead, crossHair, superimposeHeatmapToImage,
                              drawBBoxesOnImage, getImageFileSize, pointToHeatmap)
from utils.qtUtils import moveToCenter
import os


# TODO: 1. space+(0,1,2,3,4) for class label and move to next image     -> finished
#       2. get image position                                           -> finished
#       3. get the Eyetracker in                                        -> finished
#       4. get the photoshop-like opening                               -> finished
#       5. image resize                                                 -> finished
#       6. logging, all the data should be saved in csv.                -> finished
#       7. Add user hint                                                -> finished
#       8. Add bbox support                                             -> finished
#       9. Add folder selector                                          -> Replaced with config.json
#       10.Add Dark Mode                                                -> finished
#       11.add name text Box and where you want to save                 -> finished
#       12.setting in config.json                                       -> finished
#       13.Add 'Last image' button


def getPointInImage(absPoint, imPosition,boxPosition):
    xi, yi = [absPoint[0] - imPosition[0], absPoint[1] - imPosition[1]]
    xb,yb=[absPoint[0] - boxPosition[0], absPoint[1] - boxPosition[1]]
    if xi < 0 or xi >imPosition[2] or yi<0 or yi>imPosition[3] or xb<0 or xb>boxPosition[2]or yb<0 or yb>boxPosition[3]:
        return None
    return [xi, yi]


# The data we want to collect
class Data:
    def __init__(self, fileName: str):
        self.fileName = fileName
        self.classLabel = -1
        self.gazeData = []
        self.bboxs = []
        self.userGazePoint = (-1, -1)


class MainWindow(QWidget):
    def __init__(self, imageDimension: int):
        super().__init__()
        config = json.load(open('config.json'))
        imageDir = config["image folder"]
        self.imageList = glob.glob(imageDir + '/*.jpg') + glob.glob(imageDir + '/*.png')
        if config["random display order"]:
            random.shuffle(self.imageList)
        self.displaygaze=config["display gaze"]
        self.savegaze=config["save gaze"]
        self.saveheat=config["save heat"]
        self.savepicfile=config["save pic to"]
        # Only one of the mode would work
        self.cheaterMode = config["guide mode"]
        self.instaReviewMode = config["insta review"]
        # the cheater mode, insta review mode, etc, is some kind of extension. self.displayingExtension
        # is a flag of whether the displaying content is a extension.
        self.displayingExtension = False
        self.imageListIndex = 0
        self.data = Data(fileName=self.imageList[0])
        self.imageHeight = config["image height"]
        self.createControlBox()
        self.allowDrawBbox = False
        # This is for the time recording
        self.stopWatch = time.time()

        # design window image height: control height = 7:1
        layout = QGridLayout()
        self.setLayout(layout)
        if imageDimension == 2:
            self.createImageBox2D()
        elif imageDimension == 3:
            self.createImageBox3D()
        else:
            raise Exception('imageDimension must 2 or 3.')
        layout.addWidget(self.imageBox, 0, 0, 1, 1)
        layout.addWidget(self.controlBox, 1, 0, 1, 1)
        layout.setRowStretch(0, 7)
        layout.setRowStretch(1, 1)
        self.setWindowTitle("Mic Eye 2.1-beta")
        font = QFont(config['font'], 12)
        font.setBold(True)
        self.setFont(font)
        self.image=None

        self.imagewidth=None

    # This part is about eye track log system
    def setLogSystem(self, volunteerName: str, saveTo: str):
        self.logSystem = CsvLog(volunteerName, saveTo)

    def saveData(self):
        self.logSystem.log(imgName=self.data.fileName,
                           imgClass=self.data.classLabel,
                           gazeData=self.data.gazeData,
                           bboxs=self.data.bboxs,
                           userGazePoint=self.data.userGazePoint)

    def moveEvent(self,event):
        center=self.imageBox.rect().center()-QPoint(self.imageLabel.width()//2,self.imageLabel.height()//2)
        self.imageLabel.setGeometry(center.x(),center.y(),self.imageLabel.width(),self.imageLabel.height())
    
    def closeEvent(self, event):
        self.saveData()
        self.saveCurrentImage()
        event.accept()

    # This function controls all the keyboard event
    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key_Space:
            self.nextImage()

        elif key == Qt.Key_Escape and self.displayingExtension:
            self.nextImage()
            self.displayingExtension = False

        elif (Qt.Key_0 <= key <= Qt.Key_9) and not self.displayingExtension:
            print("time: ",time.time()-self.stopWatch)
            self.data.classLabel = chr(key)
            if self.instaReviewMode:
                self.instaReview()
                self.displayingExtension = True
            elif self.cheaterMode:
                self.cheaterDisplay()
                self.displayingExtension = True
            else:
                self.nextImage()
        elif key == Qt.Key_L:
            self.drawCrossHair()

    # This part is about bbox drawing
    def __setAllowDrawBboxTrue(self):
        self.allowDrawBbox = True

    def __setAllowDrawBboxFalse(self):
        self.allowDrawBbox = False

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.dragpos=QPoint(0,0)
            if not self.imageLabel.underMouse():
                return

            if self.allowDrawBbox:
                self.__bboxStartX = event.x()
                self.__bboxStartY = event.y()
                self.latermap=self.imageLabel.pixmap().copy()

            else:
                self.__dragStartPos = event.pos()
                self.__imageLabelStartPos = self.imageLabel.pos()
                

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if not self.imageLabel.underMouse():
            return

        if not self.allowDrawBbox:
            dragPos = event.pos() - self.__dragStartPos
            self.imageLabel.move(self.__imageLabelStartPos + dragPos)
            self.imageLabel.adjustSize()
            self.dragpos=dragPos
        
        else:
            thisBbox = (self.__bboxStartX, self.__bboxStartY, event.x(), event.y())
            imageX, imageY = (self.imageLabel.frameGeometry().x() + self.imageBox.frameGeometry().x(),
                            self.imageLabel.frameGeometry().y() + self.imageBox.frameGeometry().y())
            thisBbox = (thisBbox[0] - imageX, thisBbox[1] - imageY, thisBbox[2] - thisBbox[0], thisBbox[3] - thisBbox[1],self.imagescale)
            map=self.latermap.copy()

            painter = QPainter(map)
            painter.setPen(QPen(Qt.red, 2))
            rect = QRect(thisBbox[0],thisBbox[1],thisBbox[2],thisBbox[3])
            painter.drawRect(rect)
            painter.end()
            self.imageLabel.setPixmap(map)


    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if not self.imageLabel.underMouse():
                return

            if self.allowDrawBbox:
                thisBbox = (self.__bboxStartX, self.__bboxStartY, event.x(), event.y())
                imageX, imageY = (self.imageLabel.frameGeometry().x() + self.imageBox.frameGeometry().x(),
                                self.imageLabel.frameGeometry().y() + self.imageBox.frameGeometry().y())
                thisBbox = (thisBbox[0] - imageX, thisBbox[1] - imageY, thisBbox[2] - thisBbox[0], thisBbox[3] - thisBbox[1],self.imagescale)
                self.data.bboxs.append(thisBbox)
                self.allowDrawBbox = False
                painter = QPainter(self.imageLabel.pixmap())
                painter.setPen(QPen(Qt.red, 4))
                for bbox in self.data.bboxs:
                    scaleredio=self.imagescale/bbox[4]
                    rect = QRect(bbox[0]*scaleredio,bbox[1]*scaleredio,bbox[2]*scaleredio,bbox[3]*scaleredio)
                    painter.drawRect(rect)
                painter.end()
                self.imageLabel.setPixmap(self.imageLabel.pixmap())
            else:
                pass

    def wheelEvent(self, event):
        angle = event.angleDelta() / 8
        angleY = angle.y()
        if angleY > 0:
            self.imagescale *= 1.1
            diffscale=1.1
        else:
            self.imagescale *= 0.9
            diffscale=0.9
        diffbefore=self.imageLabel.pos()-self.imageBox.rect().center()
        pixmap = QPixmap(self.imageList[self.imageListIndex])
        scaledPixmap = pixmap.scaled(int(pixmap.width() * self.imagescale), int(pixmap.height() * self.imagescale))
        self.imageLabel.setPixmap(scaledPixmap)
        self.imageLabel.setFixedSize(scaledPixmap.size())
        layout = QVBoxLayout()
        layout.addWidget(self.imageLabel)
        self.imageBox.setLayout(layout)
        posafter=self.imageBox.rect().center()+QPoint(diffbefore.x()*diffscale,diffbefore.y()*diffscale)
        self.imageLabel.setGeometry(posafter.x(),posafter.y(),self.imageLabel.width(),self.imageLabel.height())
        self.imageLabel.adjustSize()
        painter = QPainter(self.imageLabel.pixmap())
        painter.setPen(QPen(Qt.red, 6))
        for bbox in self.data.bboxs:
            scaleredio=self.imagescale/bbox[4]
            rect = QRect(bbox[0]*scaleredio,bbox[1]*scaleredio,bbox[2]*scaleredio,bbox[3]*scaleredio)
            painter.drawRect(rect)
        painter.end()
             
    def getImageGeometry(self):
        windowGeometry = self.frameGeometry()
        imageGeometry = self.imageLabel.frameGeometry()
        boxGeometry = self.imageBox.frameGeometry()
        imageAbsGeometry = (windowGeometry.x() + imageGeometry.x() + boxGeometry.x(),
                            windowGeometry.y() + imageGeometry.y() + boxGeometry.y(),
                            imageGeometry.width(),
                            imageGeometry.height())
        return imageAbsGeometry
    
    def getBoxGeometry(self):
        windowGeometry = self.frameGeometry()
        boxGeometry = self.imageBox.frameGeometry()
        boxAbsGeometry = (windowGeometry.x() + boxGeometry.x(),
                            windowGeometry.y() + boxGeometry.y(),
                            boxGeometry.width(),
                            boxGeometry.height())
        return boxAbsGeometry
    def drawCrossHair(self):
        image = imRead(self.imageList[self.imageListIndex], targetHeight=self.imageHeight)
        if len(image.shape) == 2:
            # if image is grayscale, make it RGB
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        gaze = getPointInImage(getGazeCenter(lastN=30), self.getImageGeometry())
        crossHair(image, center=(gaze[0], gaze[1]))
        self.imageLabel.setPixmap(createPixmapFromArray(image))

    def nextImage(self):
        self.saveCurrentImage()
        self.saveData()
        self.imageListIndex+=1
        pixmap = QPixmap(self.imageList[self.imageListIndex])
        
        self.imageLabel.setFixedSize(self.imageBox.size())
        widrid=self.imageLabel.width()/pixmap.width()
        heightrid=self.imageLabel.height()/pixmap.height()
        self.imagescale=min(widrid,heightrid)

        scaledPixmap = pixmap.scaled(int(pixmap.width() * self.imagescale), int(pixmap.height() * self.imagescale))
        self.imageLabel.setPixmap(scaledPixmap)

        self.imageLabel.setFixedSize(scaledPixmap.size())
        
        layout = QVBoxLayout()
        layout.addWidget(self.imageLabel)
        self.imageBox.setLayout(layout)
        center=self.imageBox.rect().center()-QPoint(self.imageLabel.width()//2,self.imageLabel.height()//2)
        self.imageLabel.setGeometry(center.x(),center.y(),self.imageLabel.width(),self.imageLabel.height())
        # reset the eye tracker and stop watch
        # getGazeRaw()
        self.stopWatch=time.time()
        self.data = Data(self.imageList[self.imageListIndex])
        
    def instaReview(self):
        currentImageFile = self.imageList[self.imageListIndex]
        labels = parseLabelmeXMl(currentImageFile)
        currentImage = imRead(self.imageList[self.imageListIndex], targetHeight=self.imageHeight)
        _, originalHeight = getImageFileSize(currentImageFile)
        currentImageWithBBoxes = drawBBoxesOnImage(currentImage, labels, scaleFactor=self.imageHeight / originalHeight)
        gazeHeatmap = pointToHeatmap(self.data.gazeData, heatmapShape=currentImage.shape)
        print(gazeHeatmap.shape,currentImageWithBBoxes.shape)
        imageWithHeatmap = superimposeHeatmapToImage(heatmap=gazeHeatmap, image=currentImageWithBBoxes)
        self.imageLabel.setPixmap(createPixmapFromArray(imageWithHeatmap))

    def cheaterDisplay(self):
        nextImageFile = self.imageList[self.imageListIndex + 1]
        nextImage = imRead(nextImageFile, targetHeight=self.imageHeight)
        _, originalHeight = getImageFileSize(nextImageFile)
        imageWithBBoxes = drawBBoxesOnImage(nextImage, bboxes=parseLabelmeXMl(nextImageFile),
                                            scaleFactor=self.imageHeight / originalHeight)
        self.imageLabel.setPixmap(createPixmapFromArray(imageWithBBoxes))

    # def drawBBox(self, x1, y1, x2, y2):
    #     currentImage = imRead(self.imageList[self.imageListIndex], targetHeight=self.imageHeight)
    #     cv2.rectangle(img=currentImage,
    #                   pt1=(x1, y1),
    #                   pt2=(x2, y2),
    #                   color=(100, 0, 0),
    #                   thickness=5)
    #     self.imageLabel.setPixmap(createPixmapFromArray(currentImage))

    def drawAttentionMap(self):
        pass
    
    def gazestart(self):
        eyeTrackerInit()
        self.refreshTimer = QTimer(self)
        self.refreshTimer.start(10)
        self.refreshTimer.timeout.connect(self.refresh)

    # This function create the UI of Image Display, which centers the label within the imageBox
    def createImageBox2D(self):
        self.imageBox = QGroupBox("")
        self.imageBox.setMinimumSize(200, 200) 
        self.imageLabel = QLabel()
        pixmap = QPixmap(self.imageList[0])
        self.imageLabel.setFixedSize(self.imageBox.size())
        widrid=self.imageLabel.width()/pixmap.width()
        heightrid=self.imageLabel.height()/pixmap.height()
        self.imagescale=min(widrid,heightrid)

        scaledPixmap = pixmap.scaled(int(pixmap.width() * self.imagescale), int(pixmap.height() * self.imagescale))
        self.imageLabel.setPixmap(scaledPixmap)
        layout = QVBoxLayout()
        layout.addWidget(self.imageLabel)
        self.imageBox.setLayout(layout)
        center=self.imageBox.rect().center()-QPoint(self.imageLabel.width()//2,self.imageLabel.height()//2)
        self.imageLabel.setGeometry(center.x(),center.y(),self.imageLabel.width(),self.imageLabel.height())
        
        # self.imageLabel.setFrameStyle(QFrame.Box | QFrame.Plain)
        # self.imageLabel.setLineWidth(2)
        # self.imageLabel.setStyleSheet("border-color: red;")
        # self.imageBox.setStyleSheet("QGroupBox { border: 2px solid red; }")

    # This function create the UI of control panel
    def createControlBox(self):
        self.controlBox = QGroupBox("")
        nextButton = QPushButton("Next Image")
        lastButton = QPushButton("Last Image")
        bboxButton = QPushButton("Add Bounding Boxes")
        closeButton = QPushButton("Finish Experiment")
        #resetButton = QPushButton("Resetbotton")

        nextButton.clicked.connect(self.nextImage)
        closeButton.clicked.connect(self.close)
        bboxButton.clicked.connect(self.__setAllowDrawBboxTrue)
        layout = QHBoxLayout()
        layout.addWidget(nextButton)
        layout.addWidget(lastButton)
        layout.addWidget(bboxButton)
        layout.addWidget(closeButton)
        self.controlBox.setLayout(layout)
    
    def refresh(self):
        gaze = getGazeCenter()
        if not gaze:
            return
        gaze = getPointInImage(gaze, self.getImageGeometry(),self.getBoxGeometry())
        if not gaze:
            return
        self.data.gazeData.append([gaze,self.imagescale])
        if self.displaygaze==True:
            painter = QPainter(self.imageLabel.pixmap())
            painter.setPen(QPen(Qt.red, 2))
            for gaze in self.data.gazeData:
                painter.drawEllipse(gaze[0][0]*self.imagescale/gaze[1] - 1, gaze[0][1]*self.imagescale/gaze[1]-1 , 2, 2)
            painter.end()

    def saveCurrentImage(self):
        if self.savegaze:
            if self.displaygaze:
                pixmap = self.imageLabel.pixmap().copy()
                if pixmap is not None:
                    filename = self.savepicfile+'\\'+self.imageList[self.imageListIndex] + '.jpg'
                    pixmap.save(filename, "JPEG", quality=100)
            else:
                pixmap = self.imageLabel.pixmap().copy()
                painter = QPainter(pixmap)
                painter.setPen(QPen(Qt.red, 2))
                for gaze in self.data.gazeData:
                    painter.drawEllipse(gaze[0][0]*self.imagescale/gaze[1] - 1, gaze[0][1]*self.imagescale/gaze[1]-1 , 2, 2)
                painter.end()

                if pixmap is not None:
                    filename = self.savepicfile+'\\'+self.imageList[self.imageListIndex] + '.jpg'
                    pixmap.save(filename, "JPEG", quality=100)

        if self.saveheat:
            pixmap=self.imageLabel.pixmap().copy()
            currentImageFile =self.savepicfile+'\\'+str(self.imageListIndex) + '.jpg'
            pixmap.save(currentImageFile, "JPEG", quality=100)
            labels = parseLabelmeXMl(currentImageFile)
            currentImage = imRead(currentImageFile, targetHeight=self.imageHeight)
            _, originalHeight = getImageFileSize(self.imageList[self.imageListIndex])
            imagescale=self.imageHeight/originalHeight
            gazeHeatmap = pointToHeatmap(self.data.gazeData, heatmapShape=currentImage.shape,imagescale=imagescale)
            print(gazeHeatmap.shape,currentImage.shape)
            imageWithHeatmap = superimposeHeatmapToImage(heatmap=gazeHeatmap, image=currentImage)
            filename = self.savepicfile+'\\'+str(self.imageListIndex) + 'withheat.jpg'
            createPixmapFromArray(imageWithHeatmap).save(filename, "JPEG", quality=100)