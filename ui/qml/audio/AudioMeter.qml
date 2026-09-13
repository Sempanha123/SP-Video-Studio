import QtQuick 2.15
import "../theme"
Rectangle {
    id:root
    property real peakDb:-60
    property real rmsDb:-60
    property bool vertical:true
    property string meterName:"Audio peak"
    implicitWidth:vertical?7:90
    implicitHeight:vertical?82:7
    radius:4
    color:Theme.colors.surfacePressed
    Accessible.name: meterName + ", " + Number(peakDb).toFixed(1) + " decibels peak"
    Accessible.role: Accessible.Indicator
    Rectangle {
        anchors.bottom:parent.bottom
        width:root.vertical?parent.width:Math.max(0,parent.width*level)
        height:root.vertical?Math.max(0,parent.height*level):parent.height
        radius:parent.radius
        property real level:Math.max(0,Math.min(1,(root.peakDb+60)/60))
        color:root.peakDb>-1?Theme.colors.danger:(root.peakDb>-8?Theme.colors.warning:Theme.colors.success)
        Behavior on height { NumberAnimation { duration:Theme.animation.fast } }
        Behavior on width { NumberAnimation { duration:Theme.animation.fast } }
    }
}
