import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Rectangle {
    id: root
    property var rowData: ({})
    property bool selected: false
    property bool editing: false
    signal selectRequested(bool value)
    signal editRequested()
    signal textCommitted(string text)
    signal timingCommitted(string startText, string endText)
    signal playRequested()
    signal regenerateRequested()
    height: Math.max(54, Math.round(54 * Theme.textScale))
    color: selected ? Theme.colors.surfaceSelected : (mouse.containsMouse ? Theme.colors.surfaceHover : Theme.colors.surface)
    border.color: selected ? Theme.colors.accent : Theme.colors.border
    border.width: selected ? 2 : 1
    Accessible.role: Accessible.Row
    Accessible.selected: selected
    Accessible.name: (rowData.speakerName || "Unassigned speaker") + ". " + String(rowData.language || "").toUpperCase() + ". " + (rowData.durationStatusText || "Timing not generated") + ". Voice " + (rowData.voiceName || "unresolved") + ". Audio " + (rowData.audioStatusText || "not generated") + "."
    Accessible.description: "Start time " + (rowData.startText || "not set") + ". End time " + (rowData.endText || "not set") + "."

    RowLayout {
        anchors.fill: parent; anchors.leftMargin: 6; anchors.rightMargin: 6; spacing: 6
        CheckBox { checked: root.selected; Accessible.name: "Select speech block"; onToggled: root.selectRequested(checked); Layout.preferredWidth: 28 }
        Loader { Layout.preferredWidth: 86; sourceComponent: timeEditor; property string value: rowData.startText || "—"; property bool startField: true }
        Loader { Layout.preferredWidth: 86; sourceComponent: timeEditor; property string value: rowData.endText || "—"; property bool startField: false }
        Text { id:speakerLabel; Layout.preferredWidth: 110; text: rowData.speakerName || "Unassigned"; elide: Text.ElideRight; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; ToolTip.visible: speakerHover.hovered && speakerLabel.truncated; ToolTip.text: text; ToolTip.delay: Theme.tooltipDelay; HoverHandler{id:speakerHover} }
        Text { Layout.preferredWidth: 62; text: (rowData.language || "").toUpperCase(); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Item {
            Layout.fillWidth: true; Layout.minimumWidth: 260; Layout.preferredHeight: Math.max(42, 42 * Theme.textScale)
            Text { anchors.fill: parent; anchors.margins: 5; visible: !root.editing; text: rowData.text || ""; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; lineHeightMode: Text.ProportionalHeight; lineHeight: Theme.type.multilingualLineHeight
                MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; onDoubleClicked: root.editRequested() }
            }
            Loader { anchors.fill: parent; active: root.editing; sourceComponent: Component { AppTextField { id: edit; accessibleName: "Speech text"; text: rowData.text || ""; focus: true; Keys.onPressed: function(event){ if(event.key===Qt.Key_Return && (event.modifiers&Qt.ControlModifier)){ root.textCommitted(text); event.accepted=true } else if(event.key===Qt.Key_Escape){ root.textCommitted(text); event.accepted=true } }; onEditingFinished: root.textCommitted(text) } } }
        }
        Text { id:voiceLabel; Layout.preferredWidth: 105; text: rowData.voiceName || "Unresolved"; elide: Text.ElideRight; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; ToolTip.visible: voiceHover.hovered && voiceLabel.truncated; ToolTip.text: text; ToolTip.delay: Theme.tooltipDelay; HoverHandler{id:voiceHover} }
        StatusBadge { Layout.preferredWidth: 126; text: rowData.durationStatusText || "Not Generated"; status: (rowData.timingStatus === "fits" ? "ready" : (rowData.timingStatus === "very_long" ? "error" : "warning")) }
        StatusBadge { Layout.preferredWidth: 106; text: rowData.audioStatusText || "Not Generated"; status: (rowData.audioStatus === "ready" ? "ready" : (rowData.audioStatus === "failed" ? "error" : (rowData.audioStatus === "outdated" ? "outdated" : "warning"))) }
        RowLayout { Layout.preferredWidth: 92; spacing: 2
            IconButton { iconName: "play"; tooltip: "Play generated voice"; accessibleName: "Play generated speech"; enabled: !!rowData.activeGeneratedAudioId; onClicked: root.playRequested() }
            IconButton { iconName: "refresh"; tooltip: "Regenerate this speech"; accessibleName: "Generate speech audio"; visible: rowData.canGenerate; onClicked: root.regenerateRequested() }
        }
    }
    Component {
        id: timeEditor
        AppTextField {
            accessibleName: startField ? "Start time" : "End time"
            tooltip: startField ? "Speech start time" : "Speech end time"
            text: value
            enabled: rowData.speechSourceType !== "none"
            onEditingFinished: root.timingCommitted(startField ? text : (rowData.startText || ""), startField ? (rowData.endText || "") : text)
        }
    }
}
