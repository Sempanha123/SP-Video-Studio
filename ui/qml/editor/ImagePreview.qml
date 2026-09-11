import QtQuick 2.15
import "../theme"

Item {
    id: root
    property string sourceUrl: ""

    Image {
        anchors.fill: parent
        anchors.margins: Theme.spacing.lg
        source: root.sourceUrl
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        cache: false
        smooth: true
        autoTransform: true
        sourceSize.width: Math.min(width * 2, 1920)
        sourceSize.height: Math.min(height * 2, 1920)
    }
}
