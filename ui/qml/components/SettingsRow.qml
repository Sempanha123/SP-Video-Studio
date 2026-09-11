import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

Item {
    id: root
    property string title: ""
    property string description: ""
    default property alias actionData: actionHost.data
    implicitHeight: Math.max(textColumn.implicitHeight, actionHost.implicitHeight, 38)
    Layout.fillWidth: true

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spacing.xl
        ColumnLayout {
            id: textColumn
            Layout.fillWidth: true
            spacing: 2
            Text {
                text: root.title
                color: Theme.colors.textPrimary
                font.family: Theme.type.family
                font.pixelSize: Theme.type.body
                font.weight: Theme.type.medium
                Layout.fillWidth: true
            }
            Text {
                visible: root.description.length > 0
                text: root.description
                color: Theme.colors.textMuted
                font.family: Theme.type.family
                font.pixelSize: Theme.type.caption
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
        RowLayout {
            id: actionHost
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            spacing: Theme.spacing.sm
        }
    }
}
