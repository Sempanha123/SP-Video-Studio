import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id:root
    property var master:({})
    property var controller
    implicitWidth:150;implicitHeight:Math.max(274,Math.round(274*Theme.textScale))
    accessibleName:"Master output. Gain "+Number(master.masterGainDb||0).toFixed(1)+" decibels. "+(master.limiterEnabled?"Limiter on":"Limiter off")
    ColumnLayout { anchors.fill:parent;anchors.margins:Theme.spacing.sm;spacing:Theme.spacing.sm
        Text { text:"Master";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.heading;font.weight:Theme.type.semibold }
        RowLayout { Layout.fillWidth:true
            StatusBadge { text:master.limiterEnabled?"Limiter On":"Limiter Off";status:master.limiterEnabled?"ready":"unknown" }
            Item { Layout.fillWidth:true }
            AppSwitch { accessibleName:"Master limiter"; checked:master.limiterEnabled!==false;onToggled:if(root.controller)root.controller.setMasterLimiter(checked) }
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            AudioMeter { peakDb: Number(master.peakDb || -60); accessibleName: "Master peak level" }
            Slider {
                id: masterGain
                orientation: Qt.Vertical
                from: -60; to: 12; value: Number(master.masterGainDb || 0); stepSize: .5
                Layout.preferredHeight: 128
                Accessible.name: "Master gain, " + Number(value).toFixed(1) + " decibels"
                Accessible.role: Accessible.Slider
                property bool initialized: false
                Component.onCompleted: initialized = true
                onValueChanged: if (initialized && activeFocus && !pressed && controller) controller.setMasterGain(value)
                onPressedChanged: if (!pressed && controller) controller.setMasterGain(value)
            }
        }
        Text { Layout.alignment:Qt.AlignHCenter;text:Number(master.masterGainDb||0).toFixed(1)+" dB";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
        Text { Layout.fillWidth:true;text:master.normalizationEnabled?"Loudness normalization enabled":"Peak-safe final output";wrapMode:Text.WordWrap;color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
    }
}
