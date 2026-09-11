import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item {
    id: root
    property var controller
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.md
        RowLayout { Layout.fillWidth: true
            SectionHeader { Layout.fillWidth: true; title: "Story Outline"; subtitle: root.controller && root.controller.outline.id ? ((root.controller.beats.length||0)+" beats · "+(root.controller.outline.status||"draft")) : "Create a deterministic structure, then edit it freely." }
            SecondaryButton { text: "Undo"; onClicked: if(root.controller) root.controller.undo() }
            SecondaryButton { text: "Redo"; onClicked: if(root.controller) root.controller.redo() }
            SecondaryButton { text: "Fit Duration"; onClicked: if(root.controller) root.controller.fitDuration() }
            SecondaryButton { text: "Refresh Unlocked"; onClicked: if(root.controller) root.controller.refreshStructure() }
            AppButton { text: root.controller && root.controller.outline.id ? "Approve" : "Create Outline"; onClicked: if(root.controller) { if(root.controller.outline.id) root.controller.approveOutline(); else root.controller.createOutline(false,"") } }
        }
        RowLayout { Layout.fillWidth: true; visible: root.controller && root.controller.outline.id
            Text { text: "Target "+Math.round((root.controller.story.targetDurationMs||0)/1000)+" sec"; color: Theme.colors.textSecondary }
            Text { text: "Outline "+Math.round((root.controller.story.outlineDurationMs||0)/1000)+" sec"; color: Theme.colors.textSecondary }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "+ Beat"; onClicked: if(root.controller) root.controller.addBeat("New Beat","custom",5000) }
        }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            Column { width: parent.width; spacing: Theme.spacing.sm
                Repeater { model: root.controller ? root.controller.beats : []; StoryBeatCard { beat: modelData; controller: root.controller } }
            }
        }
        EmptyState { Layout.fillWidth: true; Layout.fillHeight: true; visible: !root.controller || !root.controller.outline.id; title: "Create your story structure"; description: "Manual and deterministic planning works fully offline."; actionText: "Create Story Plan"; onActionRequested: if(root.controller) root.controller.createOutline(false,"") }
    }
}
