import QtQuick 2.15

Image {
    property string name: "home"
    source: "../../../resources/icons/" + name + ".svg"
    fillMode: Image.PreserveAspectFit
    smooth: true
    mipmap: true
    sourceSize.width: width * 2
    sourceSize.height: height * 2
}
