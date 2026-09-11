import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

ColumnLayout {
    id: root
    property real progress: 0
    property string downloadedText: ""
    property string totalText: ""
    property real speedBytes: 0
    property string currentFile: ""
    spacing: Theme.spacing.xs

    function speedText(value) {
        if (value <= 0) return "Starting…"
        if (value >= 1024 * 1024) return (value / (1024 * 1024)).toFixed(1) + " MB/s"
        return (value / 1024).toFixed(0) + " KB/s"
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 7
        radius: 4
        color: Theme.colors.surfacePressed
        Rectangle {
            width: parent.width * Math.max(0, Math.min(1, root.progress))
            height: parent.height
            radius: parent.radius
            color: Theme.colors.accent
            Behavior on width { NumberAnimation { duration: Theme.animation.fast } }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Text {
            text: root.totalText.length > 0 ? (root.downloadedText + " / " + root.totalText) : root.downloadedText
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
        }
        Item { Layout.fillWidth: true }
        Text {
            text: root.speedText(root.speedBytes)
            color: Theme.colors.textMuted
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
        }
    }
    Text {
        visible: root.currentFile.length > 0
        Layout.fillWidth: true
        text: root.currentFile
        color: Theme.colors.textMuted
        font.family: Theme.type.family
        font.pixelSize: Theme.type.caption
        elide: Text.ElideMiddle
    }
}
