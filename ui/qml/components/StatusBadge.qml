import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
Rectangle {
    id: root
    property string text: "Ready"
    property string status: "neutral"
    function fg() { var s=status.toLowerCase(); if(s.indexOf("fail")>=0||s==="error"||s==="missing") return Theme.colors.danger; if(s.indexOf("warn")>=0||s.indexOf("review")>=0||s==="processing"||s==="downloading"||s==="outdated") return Theme.colors.warning; if(s==="ready"||s==="success"||s==="installed"||s==="complete"||s==="completed") return Theme.colors.success; if(s==="info"||s==="checking"||s==="running") return Theme.colors.info; return Theme.colors.textSecondary }
    function bg() { var c=fg(); if(c===Theme.colors.danger)return Theme.colors.dangerSoft; if(c===Theme.colors.warning)return Theme.colors.warningSoft; if(c===Theme.colors.success)return Theme.colors.successSoft; if(c===Theme.colors.info)return Theme.colors.infoSoft; return Theme.colors.surfaceHover }
    function symbol() { var s=status.toLowerCase(); if(s.indexOf("fail")>=0||s==="error"||s==="missing")return "!"; if(s.indexOf("warn")>=0||s.indexOf("review")>=0)return "⚠"; if(s==="outdated")return "↻"; if(s==="ready"||s==="success"||s==="installed"||s==="complete"||s==="completed")return "✓"; if(s==="checking"||s==="running"||s==="processing"||s==="downloading")return "…"; return "•" }
    implicitHeight: Math.max(24, Theme.controlHeightSmall)
    implicitWidth: badgeRow.implicitWidth + 16
    radius: 7; color: bg()
    Accessible.name: symbol() + " " + text
    Accessible.role: Accessible.StaticText
    RowLayout { id: badgeRow; anchors.centerIn: parent; spacing: 5
        Text { text: root.symbol(); color: root.fg(); font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.bold }
        Text { id: label; text: root.text; color: root.fg(); font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.medium; elide: Text.ElideRight }
    }
}
