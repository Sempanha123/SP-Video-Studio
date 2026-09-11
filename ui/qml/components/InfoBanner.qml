import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

Rectangle {
    id: root
    property string text: ""
    property string variant: "info"
    implicitHeight: content.implicitHeight + Theme.spacing.md * 2
    radius: Theme.radius.medium
    color: variant === "warning" ? Theme.colors.warningSoft : Theme.colors.infoSoft
    border.color: variant === "warning" ? Qt.rgba(Theme.colors.warning.r, Theme.colors.warning.g, Theme.colors.warning.b, 0.28) : Qt.rgba(Theme.colors.info.r, Theme.colors.info.g, Theme.colors.info.b, 0.28)

    RowLayout {
        id: content
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.sm
        Rectangle {
            width: 7; height: 7; radius: 4
            color: root.variant === "warning" ? Theme.colors.warning : Theme.colors.info
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: 5
        }
        Text {
            text: root.text
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.bodySmall
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}
