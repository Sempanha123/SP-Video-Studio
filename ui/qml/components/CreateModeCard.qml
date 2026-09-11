import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

Rectangle {
    id: root
    property string mode: "news"
    property string title: "News Studio"
    property string description: "Create source-based news videos with narration, visuals and captions."
    property string iconName: "news"
    property color accentColor: Theme.colors.news
    property bool selected: false
    signal clicked()

    implicitHeight: 142
    radius: Theme.radius.large
    color: selected ? Theme.colors.accentSoft : (mouse.containsMouse ? Theme.colors.surfaceHover : Theme.colors.surface)
    border.color: selected ? Theme.colors.accent : Theme.colors.border
    border.width: selected ? 2 : 1
    focus: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.lg
        spacing: Theme.spacing.sm
        RowLayout {
            Layout.fillWidth: true
            Rectangle {
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                radius: Theme.radius.medium
                color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, Theme.darkMode ? 0.18 : 0.12)
                Icon { anchors.centerIn: parent; width: 19; height: 19; name: root.iconName }
            }
            Item { Layout.fillWidth: true }
            Rectangle {
                visible: root.selected
                width: 18; height: 18; radius: 9
                color: Theme.colors.accent
                Text { anchors.centerIn: parent; text: "✓"; color: "white"; font.pixelSize: 11; font.bold: true }
            }
        }
        Text {
            text: root.title
            color: Theme.colors.textPrimary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.heading
            font.weight: Theme.type.semibold
            Layout.fillWidth: true
        }
        Text {
            text: root.description
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Item { Layout.fillHeight: true }
    }
    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
    Keys.onSpacePressed: clicked()
    Keys.onReturnPressed: clicked()
    Behavior on color { ColorAnimation { duration: Theme.animation.fast } }
}
