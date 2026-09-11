import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property var rowData: controller ? controller.selectedRow : ({})
    implicitWidth: 310
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.sm
        Text { text: "Speech Inspector"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        Text { Layout.fillWidth: true; text: rowData.text || "Select a speech row"; wrapMode: Text.WordWrap; maximumLineCount: 5; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        Text { text: "Speaker  ·  " + (rowData.speakerName || "—"); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Text { text: "Language  ·  " + ((rowData.language || "—").toUpperCase()); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Text { text: "Voice  ·  " + (rowData.voiceName || "—"); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Text { text: "Timing  ·  " + (rowData.startText || "—") + " → " + (rowData.endText || "—"); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Text { text: "Takes  ·  " + Number(rowData.takeCount || 0); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        RowLayout { visible: rowData.timingStatus === "long" || rowData.timingStatus === "very_long" || rowData.timingStatus === "short"; Layout.fillWidth: true
            SecondaryButton { text: "Keep Natural"; compact: true }
            SecondaryButton { text: "Fit Audio"; compact: true; onClicked: if(controller) controller.fitAudio(rowData.id) }
            SecondaryButton { text: "Extend Segment"; compact: true; onClicked: if(controller) controller.extendSegment(rowData.id) }
        }
        Text { visible: rowData.takes && rowData.takes.length > 0; text: "Generated takes"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong }
        Repeater { model: rowData.takes || []; delegate: RowLayout { required property var modelData; Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: modelData.label + (modelData.active ? " · Active" : ""); color: modelData.active ? Theme.colors.accent : Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            IconButton { iconName: "play"; tooltip: "Preview take"; onClicked: if(controller) controller.playTake(modelData.id) }
            SecondaryButton { text: "Use"; compact: true; enabled: !modelData.active; onClicked: if(controller) controller.activateTake(rowData.id, modelData.id) }
        } }
        Item { Layout.fillHeight: true }
    }
}
