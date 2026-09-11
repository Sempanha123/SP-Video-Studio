import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id: root
    property string title: "Task"
    property real value: 0.0
    implicitHeight: 92
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        Text { text: root.title; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
        ProgressBar { Layout.fillWidth: true; value: root.value }
    }
}
