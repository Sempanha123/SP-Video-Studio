import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id: root
    property string voiceName: "Alex"
    property string styleName: "News Anchor"
    property string language: "English"
    property string engineName: "Preview data"
    implicitHeight: 112
    RowLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        Rectangle {
            Layout.preferredWidth: 40; Layout.preferredHeight: 40; radius: 20
            color: Theme.colors.accentSoft
            Icon { anchors.centerIn: parent; width: 20; height: 20; name: "mic" }
        }
        ColumnLayout {
            Layout.fillWidth: true; spacing: 3
            Text { text: root.voiceName; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { text: root.styleName + "  •  " + root.language; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { text: root.engineName; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
        StatusBadge { text: "Preview"; status: "running" }
    }
}
