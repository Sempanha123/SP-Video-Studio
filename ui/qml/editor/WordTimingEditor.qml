import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
import "../components"

AppCard {
    id:root
    property int fps:30
    implicitHeight: Math.min(230, column.implicitHeight+Theme.spacing.lg*2)
    ColumnLayout { id:column; anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.sm
        RowLayout { Layout.fillWidth:true
            Text { Layout.fillWidth:true; text:"Word Timing"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
            Text { text:"ms · optional frame snap"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
        }
        ListView { id:list; Layout.fillWidth:true; Layout.fillHeight:true; model:WordTiming.words; spacing:4; clip:true; ScrollBar.vertical:ScrollBar{}
            delegate:RowLayout { required property var modelData; width:list.width; spacing:6
                AppTextField { id:wordText; Layout.fillWidth:true; text:modelData.text }
                AppTextField { id:startField; Layout.preferredWidth:78; text:String(modelData.startMs) }
                AppTextField { id:endField; Layout.preferredWidth:78; text:String(modelData.endMs) }
                CheckBox { id:snap; text:"Frame" }
                SecondaryButton { text:"Save"; compact:true; onClicked:WordTiming.updateWord(modelData.id,wordText.text,parseInt(startField.text),parseInt(endField.text),root.fps,snap.checked) }
                SecondaryButton { text:"Merge ↓"; compact:true; enabled:modelData.order<WordTiming.words.length-1; onClicked:WordTiming.mergeWords(modelData.id,WordTiming.words[modelData.order+1].id) }
            }
        }
        Text { visible:WordTiming.words.length===0; text:"No real word timestamps are available for this segment."; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
    }
}
