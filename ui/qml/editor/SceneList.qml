import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    signal createFromTranscriptRequested()

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.md

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                Text { text: "Scenes"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                Text {
                    text: root.controller ? (root.controller.summary.sceneCount || 0) + " scenes • " + ((root.controller.summary.totalDurationMs || 0) / 1000).toFixed(1) + " sec enabled" : "0 scenes"
                    color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption
                }
            }
            AppButton { text: "Add Scene"; compact: true; iconName: "add"; onClicked: if (root.controller) root.controller.addScene() }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            SecondaryButton { text: "From Script"; compact: true; enabled: !!root.controller; onClicked: if (root.controller) root.controller.createFromScript() }
            SecondaryButton { text: "From Transcript"; compact: true; enabled: !!root.controller && root.controller.transcriptOptions.length > 0; onClicked: root.createFromTranscriptRequested() }
            SecondaryButton { text: "Sync Script"; compact: true; enabled: !!root.controller; onClicked: if (root.controller) root.controller.syncScript() }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: Theme.spacing.sm
            model: root.controller ? root.controller.scenes : null
            ScrollBar.vertical: ScrollBar {}
            delegate: SceneCard {
                width: list.width - 12
                sceneId: model.sceneId
                sceneNumber: model.sceneNumber
                sceneName: model.sceneName
                durationText: model.durationText
                sceneStatus: model.sceneStatus
                statusName: model.statusName
                sceneEnabled: model.enabled
                hasMedia: model.hasMedia
                hasNarration: model.hasNarration
                hasSubtitle: model.hasSubtitle
                thumbnailUrl: model.thumbnailUrl
                sourceLabel: model.sourceLabel
                current: model.selected
                onSelectRequested: function(id) { if (root.controller) root.controller.selectScene(id) }
            }
        }
    }
}
