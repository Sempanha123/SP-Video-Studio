import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
Rectangle {
    id: root
    property string state: "Saved"
    readonly property bool failed: state.toLowerCase().indexOf("fail") >= 0
    readonly property bool unsaved: state.toLowerCase().indexOf("unsaved") >= 0
    readonly property bool saving: state.toLowerCase().indexOf("saving") >= 0
    implicitWidth: row.implicitWidth + 16; implicitHeight: 26; radius: 7
    color: failed ? Theme.colors.dangerSoft : (unsaved || saving ? Theme.colors.warningSoft : "transparent")
    RowLayout { id: row; anchors.centerIn: parent; spacing: 6; Rectangle { width: 6; height: 6; radius: 3; color: failed ? Theme.colors.danger : (unsaved || saving ? Theme.colors.warning : Theme.colors.success) }; Text { text: root.state; color: failed ? Theme.colors.danger : Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.medium } }
}
