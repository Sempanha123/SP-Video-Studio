import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../components"
import "../theme"

ColumnLayout {
    id: root
    property var controller
    spacing: Theme.spacing.md

    Icon { Layout.alignment: Qt.AlignHCenter; width: 42; height: 42; name: "video"; opacity: 0.65 }
    Text {
        Layout.alignment: Qt.AlignHCenter
        text: "This media could not be previewed."
        color: Theme.colors.textPrimary
        font.family: Theme.type.family
        font.pixelSize: Theme.type.heading
        font.weight: Theme.type.semibold
    }
    Text {
        Layout.alignment: Qt.AlignHCenter
        Layout.maximumWidth: 430
        text: root.controller && root.controller.errorMessage ? root.controller.errorMessage : "The file may use a codec not supported by the current Qt Multimedia backend."
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        color: Theme.colors.textSecondary
        font.family: Theme.type.family
        font.pixelSize: Theme.type.bodySmall
    }
    SecondaryButton {
        Layout.alignment: Qt.AlignHCenter
        text: "Reveal in Folder"
        iconName: "folder"
        onClicked: if (root.controller) root.controller.revealSelected()
    }
}
