import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Rectangle {
    id: root
    property string segmentId: ""
    property string sourceText: ""
    property string translatedText: ""
    property string timeText: ""
    property string statusName: "Pending"
    property bool reviewed: false
    property bool locked: false
    property bool edited: false
    property bool orphaned: false
    property var qualityWarnings: []
    signal textEdited(string segmentId, string text)
    signal reviewedChanged(string segmentId, bool reviewed)
    signal lockedChanged(string segmentId, bool locked)
    signal resetRequested(string segmentId)
    signal retranslateRequested(string segmentId, bool replaceManual)
    signal playRequested(int startMs)
    property int startMs: -1

    implicitHeight: Math.max(164, sourceColumn.implicitHeight + Theme.spacing.lg * 2)
    radius: Theme.radius.medium
    color: Theme.colors.surface
    border.color: reviewed ? Theme.colors.success : Theme.colors.border
    opacity: orphaned ? 0.55 : 1

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.lg

        ColumnLayout {
            id: sourceColumn
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            spacing: Theme.spacing.sm
            RowLayout {
                Layout.fillWidth: true
                Text { text: "SOURCE"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold }
                Text { text: root.timeText.length ? root.timeText : ""; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Item { Layout.fillWidth: true }
                IconButton { visible: root.startMs >= 0; iconName: "play"; tooltip: "Play source segment"; onClicked: root.playRequested(root.startMs) }
            }
            Text { Layout.fillWidth: true; text: root.sourceText; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; wrapMode: Text.WordWrap }
        }

        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.colors.border }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            spacing: Theme.spacing.sm
            RowLayout {
                Layout.fillWidth: true
                Text { text: "TRANSLATION"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold }
                StatusBadge { text: root.statusName; status: root.reviewed ? "ready" : (root.qualityWarnings.length ? "warning" : "unknown") }
                Text { visible: root.edited; text: "Edited"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Item { Layout.fillWidth: true }
                CheckBox { text: "Reviewed"; checked: root.reviewed; onToggled: root.reviewedChanged(root.segmentId, checked) }
                CheckBox { text: "Lock"; checked: root.locked; onToggled: root.lockedChanged(root.segmentId, checked) }
            }
            TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 92
                text: root.translatedText
                readOnly: root.locked || root.orphaned
                wrapMode: TextEdit.Wrap
                color: Theme.colors.textPrimary
                selectionColor: Theme.colors.accent
                font.family: Theme.type.family
                font.pixelSize: Theme.type.body
                background: Rectangle { radius: Theme.radius.medium; color: Theme.colors.background; border.color: parent.activeFocus ? Theme.colors.focus : Theme.colors.border }
                onTextChanged: if (activeFocus && !root.locked) root.textEdited(root.segmentId, text)
            }
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; visible: root.qualityWarnings.length > 0; text: root.qualityWarnings.join(" • "); color: Theme.colors.warning; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; elide: Text.ElideRight }
                SecondaryButton { text: "Reset"; compact: true; enabled: !root.locked; onClicked: root.resetRequested(root.segmentId) }
                SecondaryButton { text: "Retranslate"; compact: true; enabled: !root.locked && !root.orphaned; onClicked: root.retranslateRequested(root.segmentId, root.edited) }
            }
        }
    }
}
