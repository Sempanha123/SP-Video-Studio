import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
Rectangle {
    id: root
    property string text: "Ready"
    property string status: "neutral"
    function fg() { var s=status.toLowerCase(); if(s.indexOf("fail")>=0||s==="error"||s==="missing") return Theme.colors.danger; if(s.indexOf("warn")>=0||s.indexOf("review")>=0||s==="processing"||s==="downloading") return Theme.colors.warning; if(s==="ready"||s==="success"||s==="installed"||s==="complete"||s==="completed") return Theme.colors.success; if(s==="info"||s==="checking"||s==="running") return Theme.colors.info; return Theme.colors.textSecondary }
    function bg() { var c=fg(); if(c===Theme.colors.danger)return Theme.colors.dangerSoft; if(c===Theme.colors.warning)return Theme.colors.warningSoft; if(c===Theme.colors.success)return Theme.colors.successSoft; if(c===Theme.colors.info)return Theme.colors.infoSoft; return Theme.colors.surfaceHover }
    implicitHeight: 24; implicitWidth: label.implicitWidth + 18; radius: 7; color: bg()
    Text { id: label; anchors.centerIn: parent; text: root.text; color: root.fg(); font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.medium; elide: Text.ElideRight }
}
