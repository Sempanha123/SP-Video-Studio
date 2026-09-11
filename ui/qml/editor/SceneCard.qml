import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property string sceneId: ""
    property int sceneNumber: 0
    property string sceneName: "Scene"
    property string durationText: "0.0 sec"
    property string sceneStatus: "incomplete"
    property string statusName: "Incomplete"
    property bool sceneEnabled: true
    property bool hasMedia: false
    property bool hasNarration: false
    property bool hasSubtitle: false
    property string thumbnailUrl: ""
    property string sourceLabel: ""
    property bool current: false
    signal selectRequested(string sceneId)

    height: 112
    interactive: true
    selected: current
    opacity: sceneEnabled ? 1 : 0.58
    onClicked: selectRequested(sceneId)

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.md

        Rectangle {
            Layout.preferredWidth: 112
            Layout.fillHeight: true
            radius: Theme.radius.medium
            color: Theme.colors.surfaceHover
            clip: true
            Image {
                anchors.fill: parent
                source: root.thumbnailUrl
                fillMode: Image.PreserveAspectCrop
                visible: root.thumbnailUrl !== ""
                asynchronous: true
            }
            Text {
                anchors.centerIn: parent
                visible: root.thumbnailUrl === ""
                text: root.hasMedia ? "VIDEO" : "+ VISUAL"
                color: Theme.colors.textMuted
                font.family: Theme.type.family
                font.pixelSize: Theme.type.caption
                font.weight: Theme.type.semibold
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 3
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Scene " + root.sceneNumber; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Item { Layout.fillWidth: true }
                StatusBadge { text: root.statusName; status: root.sceneStatus }
            }
            Text { Layout.fillWidth: true; text: root.sceneName; elide: Text.ElideRight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; visible: root.sourceLabel !== ""; text: "From: " + root.sourceLabel; elide: Text.ElideRight; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacing.sm
                Text { text: root.durationText; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Text { visible: root.hasMedia; text: "Visual ✓"; color: Theme.colors.success; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Text { visible: root.hasNarration; text: "Narration ✓"; color: Theme.colors.success; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Text { visible: root.hasSubtitle; text: "Subs ✓"; color: Theme.colors.info; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Item { Layout.fillWidth: true }
            }
        }
    }
}
